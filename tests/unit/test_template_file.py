import os
import sys
import logging
import unittest
from unittest.mock import Mock
from tempfile import TemporaryDirectory

from jinja2 import Environment, StrictUndefined, TemplateNotFound, TemplateSyntaxError, UndefinedError, TemplateAssertionError
from nornir.core.task import Result, Task
from logging.handlers import BufferingHandler


# Import your function (adjust path if needed)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nornir_nautobot.plugins.tasks.template_file import template_file

# Dummy object for obj
class DummyObject:
    def __repr__(self):
        return "DummyObject"

# Mock Nornir Host
class MockHost:
    def __init__(self, name="test_host"):
        self.name = name
        self.data = {"color": "blue"}  # For attribute testing

# Set up logging
logger = logging.getLogger("test_template_file")
logger.setLevel(logging.ERROR)
default_handler = logging.StreamHandler()
default_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(default_handler)

class TestTemplateFile(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for templates
        self.path = os.path.join(os.path.dirname(__file__), "templates")
        self.task = Mock(spec=Task)
        self.task.host = MockHost()
        self.obj = DummyObject()

        # Replace logger handler with a buffering handler
        self.buffer_handler = BufferingHandler(1000)  # Capacity for log records
        self.buffer_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.handlers = [self.buffer_handler]  # Temporarily replace default handler


    def tearDown(self):
        # Restore default handler
        logger.handlers = [default_handler]

    def test_successful_render(self):
        """Test rendering a valid template."""
        result = template_file(
            task=self.task,
            template="valid.j2",
            path=self.path,
            obj=self.obj,
            logger=logger
        )
        self.assertFalse(result.failed)
        self.assertEqual(result.result, "Hello test_host!")

    def test_undefined_variable(self):
        """Test rendering with an undefined variable."""
        with self.assertRaises(UndefinedError):
            template_file(
                task=self.task,
                template="undefined_var.j2",
                path=self.path,
                obj=self.obj,
                logger=logger
            )
        log_records = [record.getMessage() for record in self.buffer_handler.buffer]
        self.assertEqual(len(log_records), 1)  # One error logged
        log_msg = log_records[0]
        self.assertIn("Error rendering template 'undefined_var.j2'", log_msg)
        self.assertIn(os.path.join(self.path, "undefined_var.j2"), log_msg)
        self.assertIn("1", log_msg)
        self.assertIn("UndefinedError", log_msg)
        self.assertIn("Message: 'name' is undefined", log_msg)



    def test_undefined_attribute(self):
        """Test rendering with an undefined attribute."""
        kwargs = {
            "var1": {"key1": "val1"}
        }
        with self.assertRaises(UndefinedError):
            template_file(
                task=self.task,
                template="undefined_attr.j2",
                path=self.path,
                obj=self.obj,
                logger=logger,
                **kwargs,
            )
        log_records = [record.getMessage() for record in self.buffer_handler.buffer]
        self.assertEqual(len(log_records), 1)  # One error logged
        log_msg = log_records[0]
        self.assertIn("Error rendering template 'undefined_attr.j2'", log_msg)
        self.assertIn(os.path.join(self.path, "undefined_attr.j2"), log_msg)
        self.assertIn("1", log_msg)
        self.assertIn("UndefinedError", log_msg)
        self.assertIn("Line: Color: {{ var1.key2 }}", log_msg)
        self.assertIn("has no attribute 'key2'", log_msg)

    def test_bad_syntax(self):
        """Test rendering with bad syntax."""
        with self.assertRaises(TemplateSyntaxError):
            template_file(
                task=self.task,
                template="bad_syntax.j2",
                path=self.path,
                obj=self.obj,
                logger=logger
            )
        log_records = [record.getMessage() for record in self.buffer_handler.buffer]
        self.assertEqual(len(log_records), 1)  # One error logged
        log_msg = log_records[0]
        self.assertIn("Error rendering template 'bad_syntax.j2'", log_msg)
        self.assertIn(os.path.join(self.path, "bad_syntax.j2"), log_msg)
        self.assertIn("2", log_msg)
        self.assertIn("TemplateSyntaxError", log_msg)
        self.assertIn("Message: unexpected char '!' at 29", log_msg)


    def test_bad_include_file(self):
        """Test rendering with a missing include file, including logger output."""

        with self.assertRaises(TemplateNotFound):
            template_file(
                task=self.task,
                template="bad_include.j2",
                path=self.path,
                obj=self.obj,
                logger=logger
            )

        log_records = [record.getMessage() for record in self.buffer_handler.buffer]
        self.assertEqual(len(log_records), 1)  # One error logged
        log_msg = log_records[0]
        self.assertIn("Error rendering template 'bad_include.j2'", log_msg)
        self.assertIn(os.path.join(self.path, "bad_include.j2"), log_msg)
        self.assertIn("2", log_msg)
        self.assertIn("TemplateNotFound", log_msg)
        self.assertIn("nonexistent.j2", log_msg)


    def test_filter_not_found(self):
        """Test rendering with an undefined filter."""
        with self.assertRaises(TemplateAssertionError):
            template_file(
                task=self.task,
                template="bad_filter.j2",
                path=self.path,
                obj=self.obj,
                logger=logger
            )
        log_records = [record.getMessage() for record in self.buffer_handler.buffer]
        self.assertEqual(len(log_records), 1)  # One error logged
        log_msg = log_records[0]
        self.assertIn("Error rendering template 'bad_filter.j2'", log_msg)
        self.assertIn(os.path.join(self.path, "bad_filter.j2"), log_msg)
        self.assertIn("1", log_msg)
        self.assertIn("TemplateAssertionError", log_msg)
        self.assertIn("Message: No filter named 'nonexistent_filter'", log_msg)

if __name__ == "__main__":
    unittest.main()