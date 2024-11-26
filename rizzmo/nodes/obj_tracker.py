import asyncio
import time
from collections.abc import Iterable
from typing import Optional

from easymesh import build_mesh_node
from easymesh.asyncio import forever

from rizzmo.config import config
from rizzmo.nodes.messages import ChangeServoPosition, Detection, Detections


def area(detection: Detection) -> float:
    return detection.box.width * detection.box.height


def get_tracked_object(
        objects: Iterable[Detection],
        labels=(
                'cat',
                'dog',
                'person',
        ),
) -> Optional[Detection]:
    labels_set = set(labels)
    objects = filter(lambda obj: obj.label in labels_set, objects)

    label_priorities = {l: len(labels) - i for i, l in enumerate(labels)}

    return max(
        objects,
        key=lambda o: (
            label_priorities[o.label],
            area(o),
        ),
        default=None,
    )


async def main():
    node = await build_mesh_node(
        name='obj-tracker',
        coordinator_host=config.coordinator_host,
    )

    maestro_cmd_topic = node.get_topic_sender('maestro_cmd')

    high_fps, low_fps = 30, 5
    low_fps_future = None

    target = None

    async def say_tracked_object(period: float = 1.) -> None:
        nonlocal target
        last_target = None

        while True:
            await asyncio.sleep(period)

            current_target = target
            if (
                    current_target is not None
                    and (last_target is None or current_target.label != last_target.label)
            ):
                await node.send('say', f'Tracking a {current_target.label}.')

            last_target = current_target

    asyncio.create_task(say_tracked_object())

    async def set_fps(fps: float) -> None:
        await node.send('set_fps_limit', fps)

    async def go_low_fps() -> None:
        await asyncio.sleep(3)
        await set_fps(low_fps)

    async def go_high_fps() -> None:
        await set_fps(high_fps)

    @maestro_cmd_topic.depends_on_listener()
    async def handle_objects_detected(topic, data: Detections):
        nonlocal low_fps_future, target

        latency = time.time() - data.timestamp
        image_width, image_height = 1280 / 2, 720 / 2

        target = get_tracked_object(data.objects)

        print()
        print(f'latency: {latency}')
        print(f'tracking: {target}')
        if target is None:
            if low_fps_future is None:
                low_fps_future = asyncio.create_task(go_low_fps())

            return

        box = target.box

        object_x = box.x + box.width / 2
        x_error = (2 * object_x / image_width) - 1

        object_y = image_height - box.y
        if target.label == 'person':
            object_y -= .3 * box.height
        else:
            object_y -= .5 * box.height
        y_error = (2 * object_y / image_height) - 1

        object_size = (box.width * box.height) / (image_width * image_height)
        z_error = min(max(-1., 3 * object_size - 1), 1.)

        print(f'(x, y, z)_error: {x_error:.2f}, {y_error:.2f}, {z_error:.2f}')

        if (x_error ** 2 + y_error ** 2) ** 0.5 <= 0.1:
            x_error = y_error = 0

            if low_fps_future is None:
                low_fps_future = asyncio.create_task(go_low_fps())
        else:
            if low_fps_future is not None:
                low_fps_future.cancel()
                low_fps_future = None
                await go_high_fps()

        x_error = min(max(-1., 1.5 * x_error), 1.)

        maestro_cmd = ChangeServoPosition(
            pan_deg=-3 * x_error,
            tilt0_deg=1 * z_error,
            tilt1_deg=-2 * y_error,
        )

        await maestro_cmd_topic.send(maestro_cmd)

    await node.listen('objects_detected', handle_objects_detected)

    await forever()


if __name__ == '__main__':
    asyncio.run(main())
