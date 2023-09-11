"""Testing file."""
# pylint: disable=duplicate-code
import os
from nornir import InitNornir
from nornir.core.task import Task, Result

# Disabling pylint for example
from nornir_utils.plugins.functions import print_result  # pylint: disable=import-error


def hello_world(task: Task) -> Result:
    """Example to show work inside of a task.

    Args:
        task (Task): Nornir Task

    Returns:
        Result: Nornir result
    """
    return Result(host=task.host, result=f"{task.host.name} says hello world!")


def main():
    """Nornir testing."""
    location = ["db913e3b-cbe0-4463-addc-816ba6a20100", "6f09aa66-96be-4b4d-955a-9c98e488f0e6"]

    my_nornir = InitNornir(
        inventory={
            "plugin": "NautobotInventory",
            "options": {
                "nautobot_url": os.getenv("NAUTOBOT_URL"),
                "nautobot_token": os.getenv("NAUTBOT_TOKEN"),
                "filter_parameters": {"location": location},
                "ssl_verify": False,
            },
        },
    )

    print(f"Hosts found: {len(my_nornir.inventory.hosts)}")
    # Print out the keys for the inventory
    print(my_nornir.inventory.hosts.keys())

    result = my_nornir.run(task=hello_world)
    print_result(result)


if __name__ == "__main__":
    main()
