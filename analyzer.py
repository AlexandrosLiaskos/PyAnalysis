# -*- coding: utf-8 -*-
"""
analyzer.py: Core AST visitor for Python code structure analysis.
"""

import ast
from collections import defaultdict
from typing import (
    Any, Dict, List, Optional, Tuple, DefaultDict, Union, cast
)

# Import type definitions from the models module
from .models import VarInfoDict, ImportInfoDict, ParamInfoDict, ParameterKind, AnalysisStats

# --- Helper Functions (Specific to AST Analysis) ---

def is_screaming_snake_case(name: str) -> bool:
    """Checks if a name follows the SCREAMING_SNAKE_CASE convention."""
    # Ensure it's a valid identifier before checking case/underscore
    if not name or not name.isidentifier():
        return False
    # Allow single-word uppercase like 'DEBUG'
    has_underscore = '_' in name
    all_upper_or_digit = all(c.isupper() or c.isdigit() or c == '_' for c in name)
    # Must contain at least one letter
    has_letter = any(c.isalpha() for c in name)

    if not has_letter: return False

    # Either all caps/digits/underscores (like DEBUG, MAX_SIZE)
    # Or specifically requires an underscore if mixed case isn't allowed implicitly by isupper()
    # Let's simplify: All upper/digit/underscore, must start with letter/underscore, must contain letter.
    # The `name.isupper()` check handles most cases like 'MY_CONST'.
    # Let's refine to the common convention: must contain an underscore OR be purely uppercase letters.
    is_upper_identifier = name.isupper() and name.isidentifier()

    # Common Screaming Snake: MY_CONSTANT, VERSION_INFO
    # Acceptable Constants: DEBUG (all caps), MAX_RETRIES
    # Not constants: my_const, MyClass, _internal
    if not name.isidentifier() or not has_letter:
         return False

    # Check if all alphabetic characters are uppercase
    all_alpha_is_upper = all(c.isupper() for c in name if c.isalpha())

    return all_alpha_is_upper and name[0] != '_' # Generally constants don't start with _

def get_node_repr(node: Optional[ast.AST], max_depth: int = 3) -> Optional[str]:
    """Creates a limited-depth string representation of an AST node for types/defaults."""
    if node is None or max_depth <= 0:
        return None if node is None else "..."

    if isinstance(node, ast.Constant):
        val_repr = repr(node.value)
        if isinstance(node.value, str) and len(val_repr) > 30:
            val_repr = val_repr[:27] + '...'
        return val_repr
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value_repr = get_node_repr(node.value, max_depth - 1)
        return f"{value_repr}.{node.attr}" if value_repr else node.attr
    elif isinstance(node, ast.Subscript):
        value_repr = get_node_repr(node.value, max_depth - 1)
        slice_repr = get_node_repr(node.slice, max_depth - 1)
        return f"{value_repr}[{slice_repr}]" if value_repr and slice_repr else "..."
    # Handle Index node for Python < 3.9 compatibility within Subscript
    elif isinstance(node, ast.Index) and hasattr(node, 'value'):
         return get_node_repr(node.value, max_depth -1) # type: ignore
    elif isinstance(node, ast.Slice):
        lower = get_node_repr(node.lower, max_depth - 1) or ""
        upper = get_node_repr(node.upper, max_depth - 1) or ""
        step = get_node_repr(node.step, max_depth - 1) or ""
        if step: return f"{lower}:{upper}:{step}"
        return f"{lower}:{upper}"
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        elts = [get_node_repr(e, max_depth - 1) or '?' for e in node.elts]
        content = ", ".join(elts)
        if len(content) > 30: content = content[:27] + '...'
        brackets = ('[', ']') if isinstance(node, ast.List) else \
                   ('(', ')') if isinstance(node, ast.Tuple) else \
                   ('{', '}')
        return f"{brackets[0]}{content}{brackets[1]}"
    elif isinstance(node, ast.Dict):
        items = []
        keys = node.keys or [] # Handle None case gracefully
        values = node.values or []
        for k, v in zip(keys, values):
            k_repr = get_node_repr(k, max_depth - 1) or '?'
            v_repr = get_node_repr(v, max_depth - 1) or '?'
            items.append(f"{k_repr}: {v_repr}")
            if len(items) >= 3 and len(keys) > 3:
                 items.append('...')
                 break
        return f"{{{', '.join(items)}}}"
    elif isinstance(node, ast.Call):
        func_repr = get_node_repr(node.func, max_depth - 1) or '?'
        args_repr = ", ".join([get_node_repr(a, max_depth - 1) or '?' for a in node.args])
        if len(args_repr) > 20: args_repr = args_repr[:17] + '...'
        # Simplified kwarg representation
        kwargs_repr = ", ...)" if node.keywords else ")"
        return f"{func_repr}({args_repr}{kwargs_repr}"
    # Handle BinOp for expressions like Union | NoneType (becomes Optional) in 3.10+
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
         left = get_node_repr(node.left, max_depth -1)
         right = get_node_repr(node.right, max_depth -1)
         if left and right:
             # Basic Optional check
             if left == "None" or right == "None":
                 return f"Optional[{left if right == 'None' else right}]"
             else:
                 return f"Union[{left}, {right}]" # Or just repr the Union?
         else: return "BinOp" # Fallback

    # Fallback for unhandled simple types or complex structures
    return type(node).__name__


# --- Core Analyzer Class ---

class CodeAnalyzer(ast.NodeVisitor):
    """
    Analyzes a Python AST using the visitor pattern to extract structure.

    Attributes:
        stats (AnalysisStats): Stores the collected analysis results.
        syntax_error (Optional[str]): Stores syntax error messages if parsing fails.
        _scope_stack: Internal stack for tracking nested scopes.
    """
    def __init__(self) -> None:
        # Initialize stats with expected keys and types for clarity
        self.stats: AnalysisStats = {
            "imports": [],
            "from_imports": defaultdict(list),
            "constants": [],
            "global_vars": [],
            "functions": {},
            "classes": {},
            "has_main_block": False,
            "module_docstring": None,
            "analysis_error": None, # Explicitly add the error key
        }
        # Stack: (scope_dict, scope_type_str, full_path_str)
        self._scope_stack: List[Tuple[Dict[str, Any], str, str]] = [(cast(Dict[str, Any], self.stats), "global", "")]
        self.syntax_error: Optional[str] = None # Separate attribute for error state

    # --- Scope Management ---

    def _get_current_scope(self) -> Tuple[Dict[str, Any], str, str]:
        """Returns the dictionary, type ('global', 'class', 'function'), and full path of the current scope."""
        return self._scope_stack[-1]

    def _push_scope(self, scope_dict: Dict[str, Any], scope_type: str, name: str) -> None:
        """Enters a new scope (function or class)."""
        _parent_scope_dict, _parent_type, parent_path = self._get_current_scope()
        full_path = f"{parent_path}.{name}" if parent_path else name
        scope_dict["full_path"] = full_path # Store full path in the scope's dict
        self._scope_stack.append((scope_dict, scope_type, full_path))

    def _pop_scope(self) -> None:
        """Exits the current scope."""
        if len(self._scope_stack) > 1:
            self._scope_stack.pop()

    def _get_enclosing_class_scope(self) -> Optional[Tuple[Dict[str, Any], str]]:
        """Finds the nearest enclosing class scope on the stack."""
        for scope_dict, scope_type, full_path in reversed(self._scope_stack):
            if scope_type == "class":
                return scope_dict, full_path
        return None

    # --- Node Processing Helpers ---

    def _get_line(self, node: ast.AST) -> Optional[int]:
        """Safely gets the line number of an AST node."""
        return getattr(node, 'lineno', None)

    def _format_variable_info(self, name: str, node: ast.AST, annotation: Optional[ast.AST] = None) -> VarInfoDict:
        """Creates a standardized dictionary for variable information."""
        return {
            "name": name,
            "type": get_node_repr(annotation),
            "line": self._get_line(node)
        }

    def _add_variable(self, name: str, node: ast.AST, annotation: Optional[ast.AST] = None) -> None:
        """Adds variable info to the appropriate list in the current scope."""
        scope_dict, scope_type, scope_path = self._get_current_scope()
        var_info = self._format_variable_info(name, node, annotation)

        # Determine target list based on scope and naming convention
        target_list_key = None
        if scope_type == "global":
            target_list_key = "constants" if is_screaming_snake_case(name) else "global_vars"
        elif scope_type == "class":
            target_list_key = "class_vars"
        elif scope_type == "function":
            target_list_key = "local_vars"

        if target_list_key:
             # Avoid adding if it's shadowing a function/class/method in the *same* scope
             # (e.g., a variable named 'method_name' inside a class)
             shadows_func = name in scope_dict.get("functions", {}) or \
                            name in scope_dict.get("methods", {}) or \
                            name in scope_dict.get("nested_functions", {})
             shadows_class = name in scope_dict.get("classes", {}) or \
                             name in scope_dict.get("nested_classes", {})

             if not (shadows_func or shadows_class):
                 scope_dict.setdefault(target_list_key, []).append(var_info)


    def _add_instance_variable(self, attr_name: str, node: ast.AST, annotation: Optional[ast.AST] = None) -> None:
        """Adds instance variable info to the enclosing class scope."""
        class_scope_info = self._get_enclosing_class_scope()
        if class_scope_info:
            class_scope_dict, _class_path = class_scope_info
            var_info = self._format_variable_info(attr_name, node, annotation)
            existing_vars = class_scope_dict.setdefault("instance_vars", [])
            # Avoid duplicates based on name only within the same class scope
            if not any(v['name'] == attr_name for v in existing_vars):
                 existing_vars.append(var_info)


    # --- Visitor Methods ---

    def visit_Module(self, node: ast.Module) -> None:
        # Use cast to assure type checker about self.stats structure
        cast(Dict[str, Any], self.stats)["module_docstring"] = ast.get_docstring(node, clean=True)
        self.generic_visit(node)
        # Note: Final sorting happens during report generation, not here.

    def visit_Import(self, node: ast.Import) -> None:
        line = self._get_line(node)
        imports_list = cast(List[ImportInfoDict], self.stats["imports"])
        for alias in node.names:
            import_info: ImportInfoDict = {
                "name": alias.name,
                "alias": alias.asname,
                "line": line
            }
            imports_list.append(import_info)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        line = self._get_line(node)
        module_name = "." * node.level + (node.module or "") # Handle relative imports
        from_imports_dict = cast(DefaultDict[str, List[ImportInfoDict]], self.stats["from_imports"])
        for alias in node.names:
            import_info: ImportInfoDict = {
                "name": alias.name,
                "alias": alias.asname,
                "line": line
            }
            from_imports_dict[module_name].append(import_info)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        parent_scope_dict, parent_scope_type, parent_path = self._get_current_scope()
        func_name = node.name
        line = self._get_line(node)

        func_type = "function"
        target_dict_key = "functions"
        is_method = parent_scope_type == "class"

        decorators = [get_node_repr(d) for d in node.decorator_list]

        if is_method:
            func_type = "instance_method"
            target_dict_key = "methods"
            is_classmethod = any(d and ('classmethod' in d) for d in decorators)
            is_staticmethod = any(d and ('staticmethod' in d) for d in decorators)
            is_property = any(d and ('property' in d or '.setter' in d or '.deleter' in d) for d in decorators)

            if is_property: func_type = "property"
            elif is_classmethod: func_type = "classmethod"
            elif is_staticmethod: func_type = "staticmethod"
            elif node.args.args: # Check convention only if no decorator clearly defines it
                first_arg_name = node.args.args[0].arg
                if first_arg_name == 'cls': func_type = "classmethod"
                elif first_arg_name != 'self': func_type = "staticmethod"
            elif not node.args.args: # No args implies static method
                func_type = "staticmethod"

        elif parent_scope_type == "function":
            target_dict_key = "nested_functions"

        # Process parameters
        params_details: List[ParamInfoDict] = []
        args = node.args
        # Positional-only args (Python 3.8+)
        if hasattr(args, 'posonlyargs'):
            for arg in args.posonlyargs:
                params_details.append({
                    "name": arg.arg, "type": get_node_repr(arg.annotation),
                    "default": None, "kind": ParameterKind.POSITIONAL_ONLY
                })

        # Positional-or-keyword args
        num_args = len(args.args)
        num_defaults = len(args.defaults)
        defaults_start_index = num_args - num_defaults
        for i, arg in enumerate(args.args):
            default_value = None
            if i >= defaults_start_index:
                default_value = get_node_repr(args.defaults[i - defaults_start_index])
            params_details.append({
                "name": arg.arg, "type": get_node_repr(arg.annotation),
                "default": default_value, "kind": ParameterKind.POSITIONAL_OR_KEYWORD
            })

        # Varargs (*args)
        if args.vararg:
            params_details.append({
                "name": args.vararg.arg, "type": get_node_repr(args.vararg.annotation),
                "default": None, "kind": ParameterKind.VAR_POSITIONAL
            })

        # Keyword-only args
        kw_defaults_dict = dict(zip([a.arg for a in args.kwonlyargs], args.kw_defaults))
        for arg in args.kwonlyargs:
            default_node = kw_defaults_dict.get(arg.arg)
            params_details.append({
                "name": arg.arg, "type": get_node_repr(arg.annotation),
                "default": get_node_repr(default_node) if default_node else None,
                "kind": ParameterKind.KEYWORD_ONLY
            })

        # Kwargs (**kwargs)
        if args.kwarg:
            params_details.append({
                "name": args.kwarg.arg, "type": get_node_repr(args.kwarg.annotation),
                "default": None, "kind": ParameterKind.VAR_KEYWORD
            })

        func_info: Dict[str, Any] = {
            "name": func_name, "line": line, "type": func_type,
            "params": params_details, "return_type": get_node_repr(node.returns),
            "decorators": [d for d in decorators if d], # Filter out None results
            "local_vars": [], "nested_functions": {}, "nested_classes": {},
            "docstring": ast.get_docstring(node, clean=True),
        }

        parent_scope_dict.setdefault(target_dict_key, {})[func_name] = func_info

        self._push_scope(func_info, "function", func_name)
        for stmt in node.body: self.visit(stmt)
        self._pop_scope()


    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        parent_scope_dict, parent_scope_type, parent_path = self._get_current_scope()
        class_name = node.name
        line = self._get_line(node)
        target_dict_key = "nested_classes" if parent_scope_type != "global" else "classes"

        class_info: Dict[str, Any] = {
            "name": class_name, "line": line,
            "base_classes": [get_node_repr(b) for b in node.bases if b],
            "decorators": [get_node_repr(d) for d in node.decorator_list if d],
            "methods": {}, "class_vars": [], "instance_vars": [], "nested_classes": {},
            "docstring": ast.get_docstring(node, clean=True),
        }

        parent_scope_dict.setdefault(target_dict_key, {})[class_name] = class_info

        self._push_scope(class_info, "class", class_name)
        for stmt in node.body: self.visit(stmt)
        self._pop_scope()


    def visit_Assign(self, node: ast.Assign) -> None:
        scope_dict, scope_type, _scope_path = self._get_current_scope()
        current_func_info = scope_dict if scope_type == "function" else None
        current_method_type = current_func_info.get("type") if current_func_info else None

        for target in node.targets:
            if isinstance(target, ast.Name):
                self._add_variable(target.id, node)
            elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                base_name = target.value.id
                attr_name = target.attr
                is_instance_method_scope = scope_type == "function" and current_method_type == "instance_method"
                is_class_method_scope = scope_type == "function" and current_method_type == "classmethod"
                is_class_body_scope = scope_type == "class"

                if base_name == 'self' and is_instance_method_scope:
                    self._add_instance_variable(attr_name, node)
                elif base_name == 'cls' and (is_class_body_scope or is_class_method_scope):
                     class_scope_info = self._get_enclosing_class_scope()
                     if class_scope_info:
                         class_scope_dict, _ = class_scope_info
                         # Add to class_vars of the enclosing class
                         # Use just attr_name for consistency with instance_vars
                         var_info = self._format_variable_info(attr_name, node)
                         existing = class_scope_dict.setdefault("class_vars", [])
                         if not any(v['name'] == attr_name for v in existing):
                             existing.append(var_info)
                     else: # cls used oddly outside class context? Treat as normal var.
                          self._add_variable(f"cls.{attr_name}", node)
                elif is_class_body_scope and base_name == class_scope_info[0]['name'] if class_scope_info else False:
                     # Assignment like `MyClass.var = ...` inside the class body
                     # Treat as class var
                     var_info = self._format_variable_info(attr_name, node)
                     existing = scope_dict.setdefault("class_vars", [])
                     if not any(v['name'] == attr_name for v in existing):
                         existing.append(var_info)

                else:
                     # Other attribute assignments (e.g., obj.attr, OtherClass.attr)
                     # Treat as a standard variable in the current scope, using the full name
                     full_attr_name = get_node_repr(target) or f"{base_name}.{attr_name}"
                     self._add_variable(full_attr_name, node)
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name): self._add_variable(elt.id, node)

        self.visit(node.value) # Visit the right-hand side


    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        scope_dict, scope_type, _scope_path = self._get_current_scope()
        current_func_info = scope_dict if scope_type == "function" else None
        current_method_type = current_func_info.get("type") if current_func_info else None
        target = node.target
        annotation = node.annotation

        if isinstance(target, ast.Name):
             self._add_variable(target.id, node, annotation)
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
             base_name = target.value.id
             attr_name = target.attr
             is_instance_method_scope = scope_type == "function" and current_method_type == "instance_method"
             is_class_method_scope = scope_type == "function" and current_method_type == "classmethod"
             is_class_body_scope = scope_type == "class"
             class_scope_info = self._get_enclosing_class_scope()

             if base_name == 'self' and is_instance_method_scope:
                  self._add_instance_variable(attr_name, node, annotation)
             elif base_name == 'cls' and (is_class_body_scope or is_class_method_scope):
                  if class_scope_info:
                      class_scope_dict, _ = class_scope_info
                      var_info = self._format_variable_info(attr_name, node, annotation)
                      existing = class_scope_dict.setdefault("class_vars", [])
                      if not any(v['name'] == attr_name for v in existing):
                         existing.append(var_info)
                  else:
                      self._add_variable(f"cls.{attr_name}", node, annotation)
             elif is_class_body_scope and base_name == class_scope_info[0]['name'] if class_scope_info else False:
                 # Annotated assignment like `MyClass.var: int = ...` inside class body
                 var_info = self._format_variable_info(attr_name, node, annotation)
                 existing = scope_dict.setdefault("class_vars", [])
                 if not any(v['name'] == attr_name for v in existing):
                    existing.append(var_info)
             elif is_class_body_scope and isinstance(target.value, ast.Name) and target.value.id == scope_dict.get("name"):
                  # Catches ClassName.var: type = value inside class body
                  var_info = self._format_variable_info(attr_name, node, annotation)
                  existing = scope_dict.setdefault("class_vars", [])
                  if not any(v['name'] == attr_name for v in existing):
                      existing.append(var_info)
             else:
                  full_attr_name = get_node_repr(target) or f"{base_name}.{attr_name}"
                  self._add_variable(full_attr_name, node, annotation)

        if node.value: self.visit(node.value)
        self.visit(annotation)


    def visit_If(self, node: ast.If) -> None:
        # Check for if __name__ == "__main__":
        is_main_check = False
        if isinstance(node.test, ast.Compare):
            test = node.test
            # Check structure: Name == Constant or Constant == Name
            is_name_eq_main = (isinstance(test.left, ast.Name) and test.left.id == '__name__' and
                               len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and
                               len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant) and
                               test.comparators[0].value == '__main__')
            is_main_eq_name = (isinstance(test.left, ast.Constant) and test.left.value == '__main__' and
                               len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) and
                               len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Name) and
                               test.comparators[0].id == '__name__')

            if is_name_eq_main or is_main_eq_name:
                 cast(Dict[str, Any], self.stats)["has_main_block"] = True
                 is_main_check = True # Optional: Could skip visiting body if needed

        # Continue visiting test, body, and orelse regardless
        self.generic_visit(node)