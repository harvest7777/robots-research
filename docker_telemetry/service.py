from typing import NewType, Any

import docker as docker_sdk

ContainerId = NewType("ContainerId", str)


class DockerService:
    def __init__(self) -> None:
        self._client = docker_sdk.from_env()
        self._containers: dict[ContainerId, Any] = {}

    def create_and_start(self, name: str, image: str) -> ContainerId:
        container = self._client.containers.run(
            image,
            name=name,
            detach=True,
        )
        cid = ContainerId(container.id)
        self._containers[cid] = container
        return cid

    def write_log(self, container_id: ContainerId, line: str) -> None:
        self._containers[container_id].exec_run(
            ['sh', '-c', 'printf "%s\n" "$T" >/proc/1/fd/1'],
            environment={'T': line},
        )

    def stop_and_remove(self, container_id: ContainerId) -> None:
        container = self._containers.pop(container_id)
        container.stop()
        container.remove()
