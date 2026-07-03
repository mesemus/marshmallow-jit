# SPDX-FileCopyrightText: 2026 CESNET z.s.p.o.
# SPDX-License-Identifier: MIT
"""Dynamic Python code building and compilation utilities.

Provides PythonCode class for constructing, formatting, and executing
dynamically generated Python code with variable management and imports.
"""

import base64
import contextlib
import keyword
from collections.abc import Generator
from typing import Any, Self, override

from marshmallow_jit.log import log

INDENTATION_STR = "    "
PROLOGUE = """
import marshmallow
from marshmallow import missing
import typing
"""


class PythonCode:
    """Builds and compiles dynamically generated Python code.

    Manages variable names, indentation, imports, and compilation into
    executable code with proper error reporting.
    """

    def __init__(self, prologue: str = PROLOGUE) -> None:
        self.lines = []
        self.indentation = 0
        self.variables: dict[str, Any] = {}
        self.prologue = prologue
        self.extra_imports = set()
        self.variable_index = 0

    def add_import_line(self, import_line: str) -> None:
        """Add an import statement to the generated code."""
        self.extra_imports.add(import_line)

    def add_variable(self, name: str, value: Any) -> str:
        """Register a variable in the execution environment and return its unique name."""
        name = self.generate_variable(name)
        self.variables[name] = value
        return name

    def is_valid_variable(self, name: str) -> bool:
        """Check if name is a valid Python identifier (not a keyword)."""
        return name.isidentifier() and not keyword.iskeyword(name)

    def generate_variable(self, name: str) -> str:
        """Generate a unique, valid Python variable name from the given base name."""
        self.variable_index += 1
        name += f"_{self.variable_index}"

        if self.is_valid_variable(name):
            return name
        name = f"var_{name}"
        if self.is_valid_variable(name):
            return name

        # remove all non-alphabetic characters and add hash
        hash = base64.b64encode(name.encode()).decode().rstrip("=")  # Remove padding
        name = "".join(c for c in name if c.isalpha())
        return f"{name}_{hash}"

    @contextlib.contextmanager
    def indent(self, indent_line: str | None) -> Generator[None]:
        """Context manager for indented code blocks.

        Optionally writes a header line before increasing indentation.
        Automatically inserts ``pass`` for empty blocks.
        """
        if indent_line:
            self.write(indent_line.rstrip() + ":")
        self.indentation += 1
        lines_before = len(self.lines)
        try:
            yield
        finally:
            # an indented block cannot be empty - if nothing was written inside it
            # (e.g. a no-op Inliner), emit a `pass` to keep the generated code valid
            if len(self.lines) == lines_before:
                self.write("pass")
            self.indentation -= 1

    def write(self, line: str) -> None:
        """Append lines to the code buffer with normalized indentation."""
        # remove all empty lines
        lines = [x for x in line.splitlines() if x.strip()]

        # normalize indentation - if the first line starts with whitespace, remove that amount
        # of whitespaces from all lines. The indentation of the first line is used as the base
        # and is arbitrary
        if lines and lines[0].startswith(" "):
            number_of_leading_whitespaces = len(lines[0]) - len(lines[0].lstrip())
            lines = [x[number_of_leading_whitespaces:] for x in lines]

        for line in lines:
            self.lines.append(INDENTATION_STR * self.indentation + line)

    def __iadd__(self, other: str) -> Self:
        """Append code lines using ``+=`` syntax."""
        self.write(other)
        return self

    @override
    def __str__(self) -> str:
        """Return the generated code as a formatted string."""
        return "\n".join(["    " * self.indentation + line for line in self.lines])

    def compile(self, environment: dict[str, Any]) -> dict[str, Any]:
        """Compile the generated code and return the execution namespace.

        Logs errors with line numbers if compilation fails.
        """
        namespace = environment.copy()
        namespace.update(self.variables)
        code = self.prologue + "\n" + "\n".join(self.extra_imports) + "\n" + str(self)
        try:
            exec(code, namespace)
        except:
            # add line numbers to the code
            code = "\n".join(f"{lineno:3d} {x}" for lineno, x in enumerate(code.splitlines(), start=1))
            log.error(f"Exception in compiling generated code:\n{code}")
            raise
        return namespace
