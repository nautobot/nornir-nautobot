"""This playbook demonstrates how to use the custom template_file task."""

import logging
import os
import tempfile

import yaml
from jinja2 import TemplateAssertionError, TemplateNotFound, TemplateSyntaxError, UndefinedError
from nornir import InitNornir

from nornir_nautobot.plugins.tasks.template_file import template_file


# Dummy object for obj
class DummyObject:  # pylint: disable=too-few-public-methods
    """A dummy object to simulate the context for template rendering."""

    def __repr__(self):
        """Return a string representation of the dummy object."""
        return "DummyObject"


# Setup logger
logger = logging.getLogger("template_file_playbook")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(handler)

# Create a temporary inventory directory with hosts.yaml
tmp_inventory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
hosts_yaml = {"test_host": {"hostname": "localhost", "data": {"color": "blue"}}}
with open(os.path.join(tmp_inventory.name, "hosts.yaml"), "w", encoding="utf8") as f:
    yaml.dump(hosts_yaml, f)
with open(os.path.join(tmp_inventory.name, "groups.yaml"), "w", encoding="utf8") as f:
    yaml.dump({}, f)

# InitNornir with SimpleInventory plugin
nr = InitNornir(
    inventory={
        "plugin": "SimpleInventory",
        "options": {
            "host_file": os.path.join(tmp_inventory.name, "hosts.yaml"),
            "group_file": os.path.join(tmp_inventory.name, "groups.yaml"),
        },
    }
)

# Path to templates directory (adjust if needed)
template_path = os.path.join(os.path.dirname(__file__), "../tests/unit/templates")
obj = DummyObject()


# Helper to run and print result or error
def run_template_example(template_name, **kwargs):
    """Run the template_file task and print the result or error."""
    try:
        result = nr.run(
            task=template_file, template=template_name, path=template_path, obj=obj, logger=logger, **kwargs
        )
        for host, r in result.items():
            if r.failed is False:
                print(f"[SUCCESS] {template_name} on {host}: {r.result}")
            else:
                print(f"[ERROR] {template_name} on {host}: \n\n{r.result}")
    except (UndefinedError, TemplateSyntaxError, TemplateNotFound, TemplateAssertionError) as e:
        print(f"[ERROR] {template_name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Uncomment the scenarios you want to test

    # 1. Successful render
    run_template_example("valid.j2")

    # 2. Undefined variable
    # run_template_example("undefined_var.j2")

    # 3. Undefined attribute
    # run_template_example("undefined_attr.j2", var1={"key1": "val1"})

    # 4. Bad syntax
    # run_template_example("bad_syntax.j2")

    # 5. Bad include file
    # run_template_example("bad_include.j2")

    # 6. Filter not found
    # run_template_example("bad_filter.j2")

    # 7. Check file indirection with include
    # run_template_example("include_with_undefined.j2")
