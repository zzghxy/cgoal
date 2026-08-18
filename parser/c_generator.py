# ------------------------------------------------------------------------------
# pycparser: c_generator.py
#
# C code generator from pycparser AST nodes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
# ------------------------------------------------------------------------------
from typing import Callable, List, Optional

from . import c_ast


class CGenerator:
    """Uses the same visitor pattern as c_ast.NodeVisitor, but modified to
    return a value from each visit method, using string accumulation in
    generic_visit.
    """

    indent_level: int
    reduce_parentheses: bool

    def __init__(self, reduce_parentheses: bool = False) -> None:
        """Constructs C-code generator

        reduce_parentheses:
            if True, eliminates needless parentheses on binary operators
        """
        # Statements start with indentation of self.indent_level spaces, using
        # the _make_indent method.
        self.indent_level = 0
        self.reduce_parentheses = reduce_parentheses

    def _make_indent(self) -> str:
        return " " * self.indent_level

    def visit(self, node: c_ast.Node) -> str:
        method = "visit_" + node.__class__.__name__
        return getattr(self, method, self.generic_visit)(node)

    def generic_visit(self, node: Optional[c_ast.Node]) -> str:
        if node is None:
            return ""
        else:
            return "".join(self.visit(c) for c_name, c in node.children())

    def visit_Constant(self, n: c_ast.Constant) -> str:
        return n.value

    def visit_ID(self, n: c_ast.ID) -> str:
        return n.name

    def visit_Pragma(self, n: c_ast.Pragma) -> str:
        ret = "#pragma"
        if n.string:
            ret += " " + n.string
        return ret
    
    def visit_Comment(self, n: c_ast.Comment) -> str:
        return n.value

    def visit_ArrayRef(self, n: c_ast.ArrayRef) -> str:
        arrref = self._parenthesize_unless_simple(n.name)
        return arrref + "[" + self._visit_str(n.subscript) + "]"

    def visit_StructRef(self, n: c_ast.StructRef) -> str:
        sref = self._parenthesize_unless_simple(n.name)
        return sref + n.type + self._visit_str(n.field)

    def visit_FuncCall(self, n: c_ast.FuncCall) -> str:
        fref = self._parenthesize_unless_simple(n.name)
        if isinstance(fref, list):
            fref = ''.join(fref)
        args = ""
        if n.args is not None:
            visited = self.visit(n.args)
            if isinstance(visited, list):
                args = ', '.join(visited)
            else:
                args = visited
        return fref + "(" + args + ")"

    def visit_UnaryOp(self, n: c_ast.UnaryOp) -> str:
        match n.op:
            case "sizeof":
                # Always parenthesize the argument of sizeof since it can be
                # a name.
                visited = self.visit(n.expr)
                if isinstance(visited, list):
                    visited = ' '.join(visited)
                return f"sizeof({visited})"
            case "p++":
                operand = self._parenthesize_unless_simple(n.expr)
                if isinstance(operand, list):
                    operand = ''.join(operand)
                return f"{operand}++"
            case "p--":
                operand = self._parenthesize_unless_simple(n.expr)
                if isinstance(operand, list):
                    operand = ''.join(operand)
                return f"{operand}--"
            case _:
                operand = self._parenthesize_unless_simple(n.expr)
                if isinstance(operand, list):
                    operand = ''.join(operand)
                return f"{n.op}{operand}"

    # Precedence map of binary operators:
    precedence_map = {
        # Should be in sync with c_parser.CParser.precedence
        # Higher numbers are stronger binding
        "||": 0,  # weakest binding
        "&&": 1,
        "|": 2,
        "^": 3,
        "&": 4,
        "==": 5,
        "!=": 5,
        ">": 6,
        ">=": 6,
        "<": 6,
        "<=": 6,
        ">>": 7,
        "<<": 7,
        "+": 8,
        "-": 8,
        "*": 9,
        "/": 9,
        "%": 9,  # strongest binding
    }

    def visit_BinaryOp(self, n: c_ast.BinaryOp) -> str:
        # Note: all binary operators are left-to-right associative
        #
        # If `n.left.op` has a stronger or equally binding precedence in
        # comparison to `n.op`, no parenthesis are needed for the left:
        # e.g., `(a*b) + c` is equivalent to `a*b + c`, as well as
        #       `(a+b) - c` is equivalent to `a+b - c` (same precedence).
        # If the left operator is weaker binding than the current, then
        # parentheses are necessary:
        # e.g., `(a+b) * c` is NOT equivalent to `a+b * c`.
        lval_str = self._parenthesize_if(
            n.left,
            lambda d: not (
                self._is_simple_node(d)
                or self.reduce_parentheses
                and isinstance(d, c_ast.BinaryOp)
                and self.precedence_map[d.op] >= self.precedence_map[n.op]
            ),
        )
        # If `n.right.op` has a stronger -but not equal- binding precedence,
        # parenthesis can be omitted on the right:
        # e.g., `a + (b*c)` is equivalent to `a + b*c`.
        # If the right operator is weaker or equally binding, then parentheses
        # are necessary:
        # e.g., `a * (b+c)` is NOT equivalent to `a * b+c` and
        #       `a - (b+c)` is NOT equivalent to `a - b+c` (same precedence).
        rval_str = self._parenthesize_if(
            n.right,
            lambda d: not (
                self._is_simple_node(d)
                or self.reduce_parentheses
                and isinstance(d, c_ast.BinaryOp)
                and self.precedence_map[d.op] > self.precedence_map[n.op]
            ),
        )
        return f"{lval_str} {n.op} {rval_str}"

    def visit_Assignment(self, n: c_ast.Assignment) -> str:
        rval_str = self._parenthesize_if(
            n.rvalue, lambda n: isinstance(n, c_ast.Assignment)
        )
        lval = self.visit(n.lvalue)
        if isinstance(lval, list):
            lval = ' '.join(lval)
        return f"{lval} {n.op} {rval_str}"

    def visit_IdentifierType(self, n: c_ast.IdentifierType) -> str:
        return " ".join(n.names)
    
    def _visit_str(self, n) -> str:
        """访问节点并确保返回字符串"""
        visited = self.visit(n)
        if isinstance(visited, list):
            return ' '.join(str(item) for item in visited)
        return str(visited)
    
    def _visit_expr(self, n: c_ast.Node) -> str:
        visited = self.visit(n)
        if isinstance(visited, list):
            visited = ' '.join(visited)
        
        match n:
            case c_ast.InitList():
                return "{" + visited + "}"
            case c_ast.ExprList() | c_ast.Compound():
                return "(" + visited + ")"
            case _:
                return visited

    def visit_Decl(self, n: c_ast.Decl, no_type: bool = False) -> str:
        # no_type is used when a Decl is part of a DeclList, where the type is
        # explicitly only for the first declaration in a list.
        #
        s = n.name if no_type else self._generate_decl(n)
        if n.bitsize:
            visited = self.visit(n.bitsize)
            if isinstance(visited, list):
                visited = ' '.join(visited)
            s += " : " + visited
        if n.init:
            s += " = " + self._visit_expr(n.init)
        return s

    def visit_DeclList(self, n: c_ast.DeclList) -> str:
        s = self.visit(n.decls[0])
        if len(n.decls) > 1:
            s += ", " + ", ".join(
                self.visit_Decl(decl, no_type=True) for decl in n.decls[1:]
            )
        return s

    def visit_Typedef(self, n: c_ast.Typedef) -> str:
        s = ""
        if n.storage:
            s += " ".join(n.storage) + " "
        s += self._generate_type(n.type)
        return s

    def visit_Cast(self, n: c_ast.Cast) -> str:
        s = "(" + self._generate_type(n.to_type, emit_declname=False) + ")"
        return s + " " + self._parenthesize_unless_simple(n.expr)

    def visit_ExprList(self, n: c_ast.ExprList) -> str:
        visited_subexprs = []
        for expr in n.exprs:
            visited_subexprs.append(self._visit_expr(expr))
        return ", ".join(visited_subexprs)

    def visit_InitList(self, n: c_ast.InitList) -> str:
        visited_subexprs = []
        for expr in n.exprs:
            visited_subexprs.append(self._visit_expr(expr))
        return ", ".join(visited_subexprs)

    def visit_Enum(self, n: c_ast.Enum) -> str:
        return self._generate_struct_union_enum(n, name="enum")

    def visit_Alignas(self, n: c_ast.Alignas) -> str:
        return "_Alignas({})".format(self.visit(n.alignment))

    def visit_Enumerator(self, n: c_ast.Enumerator) -> str:
        if not n.value:
            return "{indent}{name},\n".format(
                indent=self._make_indent(),
                name=n.name,
            )
        else:
            return "{indent}{name} = {value},\n".format(
                indent=self._make_indent(),
                name=n.name,
                value=self.visit(n.value),
            )

    def visit_FuncDef(self, n: c_ast.FuncDef) -> str:
        decl = self.visit(n.decl)
        self.indent_level = 0
        body = self.visit(n.body)
        if n.param_decls:
            knrdecls = ";\n".join(self.visit(p) for p in n.param_decls)
            return decl + "\n" + knrdecls + ";\n" + body + "\n"
        else:
            return decl + "\n" + body + "\n"

    def visit_FileAST(self, n: c_ast.FileAST) -> str:
        s = ""
        for ext in n.ext:
            match ext:
                case c_ast.FuncDef():
                    s += self.visit(ext)
                case c_ast.Pragma():
                    s += self.visit(ext) + "\n"
                case _:
                    s += self.visit(ext) + ";\n"
        return s

    def visit_Compound(self, n: c_ast.Compound) -> str:
        s = self._make_indent() + "{\n"
        self.indent_level += 2
        if n.block_items:
            s += "".join(self._generate_stmt(stmt) for stmt in n.block_items)
        self.indent_level -= 2
        s += self._make_indent() + "}\n"
        return s

    def visit_CompoundLiteral(self, n: c_ast.CompoundLiteral) -> str:
        return "(" + self._visit_str(n.type) + "){" + self._visit_str(n.init) + "}"

    def visit_EmptyStatement(self, n: c_ast.EmptyStatement) -> str:
        return ";"

    def visit_ParamList(self, n: c_ast.ParamList) -> str:
        return ", ".join(self.visit(param) for param in n.params)

    def visit_Return(self, n: c_ast.Return) -> str:
        s = "return"
        if n.expr:
            s += " " + self._visit_str(n.expr)
        return s + ";"

    def visit_Break(self, n: c_ast.Break) -> str:
        return "break;"

    def visit_Continue(self, n: c_ast.Continue) -> str:
        return "continue;"

    def visit_TernaryOp(self, n: c_ast.TernaryOp) -> str:
        s = "(" + self._visit_expr(n.cond) + ") ? "
        s += "(" + self._visit_expr(n.iftrue) + ") : "
        s += "(" + self._visit_expr(n.iffalse) + ")"
        return s

    def visit_If(self, n: c_ast.If) -> str:
        s = "if ("
        if n.cond:
            s += self.visit(n.cond)
        s += ")\n"
        s += self._generate_stmt(n.iftrue, add_indent=True)
        if n.iffalse:
            s += self._make_indent() + "else\n"
            s += self._generate_stmt(n.iffalse, add_indent=True)
        return s

    def visit_For(self, n: c_ast.For) -> str:
        s = "for ("
        if n.init:
            s += self._visit_str(n.init)
        s += ";"
        if n.cond:
            s += " " + self._visit_str(n.cond)
        s += ";"
        if n.next:
            s += " " + self._visit_str(n.next)
        s += ")\n"
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_While(self, n: c_ast.While) -> str:
        s = "while ("
        if n.cond:
            s += self.visit(n.cond)
        s += ")\n"
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_DoWhile(self, n: c_ast.DoWhile) -> str:
        s = "do\n"
        s += self._generate_stmt(n.stmt, add_indent=True)
        s += self._make_indent() + "while ("
        if n.cond:
            s += self.visit(n.cond)
        s += ");"
        return s

    def visit_StaticAssert(self, n: c_ast.StaticAssert) -> str:
        s = "_Static_assert("
        s += self.visit(n.cond)
        if n.message:
            s += ","
            s += self.visit(n.message)
        s += ")"
        return s

    def visit_Switch(self, n: c_ast.Switch) -> str:
        s = "switch (" + self._visit_str(n.cond) + ")\n"
        s += self._generate_stmt(n.stmt, add_indent=True)
        return s

    def visit_Case(self, n: c_ast.Case) -> str:
        s = "case " + self._visit_str(n.expr) + ":\n"
        for stmt in n.stmts:
            s += self._generate_stmt(stmt, add_indent=True)
        return s

    def visit_Default(self, n: c_ast.Default) -> str:
        s = "default:\n"
        for stmt in n.stmts:
            s += self._generate_stmt(stmt, add_indent=True)
        return s

    def visit_Label(self, n: c_ast.Label) -> str:
        return n.name + ":\n" + self._generate_stmt(n.stmt)

    def visit_Goto(self, n: c_ast.Goto) -> str:
        return "goto " + n.name + ";"

    def visit_EllipsisParam(self, n: c_ast.EllipsisParam) -> str:
        return "..."

    def visit_Struct(self, n: c_ast.Struct) -> str:
        return self._generate_struct_union_enum(n, "struct")

    def visit_Typename(self, n: c_ast.Typename) -> str:
        return self._generate_type(n.type)

    def visit_Union(self, n: c_ast.Union) -> str:
        return self._generate_struct_union_enum(n, "union")

    def visit_NamedInitializer(self, n: c_ast.NamedInitializer) -> str:
        s = ""
        for name in n.name:
            if isinstance(name, c_ast.ID):
                s += "." + name.name
            else:
                s += "[" + self._visit_str(name) + "]"
        s += " = " + self._visit_expr(n.expr)
        return s

    def visit_FuncDecl(self, n: c_ast.FuncDecl) -> str:
        return self._generate_type(n)

    def visit_ArrayDecl(self, n: c_ast.ArrayDecl) -> str:
        return self._generate_type(n, emit_declname=False)

    def visit_TypeDecl(self, n: c_ast.TypeDecl) -> str:
        return self._generate_type(n, emit_declname=False)

    def visit_PtrDecl(self, n: c_ast.PtrDecl) -> str:
        return self._generate_type(n, emit_declname=False)

    def _generate_struct_union_enum(
        self, n: c_ast.Struct | c_ast.Union | c_ast.Enum, name: str
    ) -> str:
        """Generates code for structs, unions, and enums. name should be
        'struct', 'union', or 'enum'.
        """
        if name in ("struct", "union"):
            assert isinstance(n, (c_ast.Struct, c_ast.Union))
            members = n.decls
            body_function = self._generate_struct_union_body
        else:
            assert name == "enum"
            assert isinstance(n, c_ast.Enum)
            members = None if n.values is None else n.values.enumerators
            body_function = self._generate_enum_body
        s = name + " " + (n.name or "")
        if members is not None:
            # None means no members
            # Empty sequence means an empty list of members
            s += "\n"
            s += self._make_indent()
            self.indent_level += 2
            s += "{\n"
            s += body_function(members)
            self.indent_level -= 2
            s += self._make_indent() + "}"
        return s

    def _generate_struct_union_body(self, members: List[c_ast.Node]) -> str:
        return "".join(self._generate_stmt(decl) for decl in members)

    def _generate_enum_body(self, members: List[c_ast.Enumerator]) -> str:
        # `[:-2] + '\n'` removes the final `,` from the enumerator list
        return "".join(self.visit(value) for value in members)[:-2] + "\n"

    def _generate_stmt(self, n: c_ast.Node, add_indent: bool = False) -> str:
        """Generation from a statement node. This method exists as a wrapper
        for individual visit_* methods to handle different treatment of
        some statements in this context.
        """
        if add_indent:
            self.indent_level += 2
        indent = self._make_indent()
        if add_indent:
            self.indent_level -= 2

        match n:
            case (
                c_ast.Decl()
                | c_ast.Assignment()
                | c_ast.Cast()
                | c_ast.UnaryOp()
                | c_ast.BinaryOp()
                | c_ast.TernaryOp()
                | c_ast.FuncCall()
                | c_ast.ArrayRef()
                | c_ast.StructRef()
                | c_ast.Constant()
                | c_ast.ID()
                | c_ast.Typedef()
                | c_ast.ExprList()
            ):
                # These can also appear in an expression context so no semicolon
                # is added to them automatically
                #
                return indent + self._visit_str(n) + ";\n"
            case c_ast.Compound():
                # No extra indentation required before the opening brace of a
                # compound - because it consists of multiple lines it has to
                # compute its own indentation.
                #
                return self._visit_str(n)
            case c_ast.If():
                return indent + self._visit_str(n)
            case _:
                return indent + self._visit_str(n) + "\n"

    def _generate_decl(self, n: c_ast.Decl) -> str:
        """Generation from a Decl node."""
        s = ""
        if n.funcspec:
            s = " ".join(n.funcspec) + " "
        if n.storage:
            s += " ".join(n.storage) + " "
        if n.align:
            visited = self.visit(n.align[0])
            if isinstance(visited, list):
                visited = ' '.join(visited)
            s += visited + " "
        s += self._generate_type(n.type)
        return s

    def _generate_type(
        self,
        n: c_ast.Node,
        modifiers: List[c_ast.Node] = [],
        emit_declname: bool = True,
    ) -> str:
        """Recursive generation from a type node. n is the type node.
        modifiers collects the PtrDecl, ArrayDecl and FuncDecl modifiers
        encountered on the way down to a TypeDecl, to allow proper
        generation from it.
        """
        # ~ print(n, modifiers)
        match n:
            case c_ast.TypeDecl():
                s = ""
                if n.quals:
                    s += " ".join(n.quals) + " "
                visited = self.visit(n.type)
                if isinstance(visited, list):
                    s += ' '.join(visited)
                else:
                    s += visited

                nstr = n.declname if n.declname and emit_declname else ""
                # Resolve modifiers.
                # Wrap in parens to distinguish pointer to array and pointer to
                # function syntax.
                #
                for i, modifier in enumerate(modifiers):
                    match modifier:
                        case c_ast.ArrayDecl():
                            if i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl):
                                nstr = "(" + nstr + ")"
                            nstr += "["
                            if modifier.dim_quals:
                                nstr += " ".join(modifier.dim_quals) + " "
                            if modifier.dim is not None:
                                visited = self.visit(modifier.dim)
                                if isinstance(visited, list):
                                    nstr += ' '.join(visited)
                                else:
                                    nstr += visited
                            nstr += "]"
                        case c_ast.FuncDecl():
                            if i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl):
                                nstr = "(" + nstr + ")"
                            args = ""
                            if modifier.args is not None:
                                visited = self.visit(modifier.args)
                                if isinstance(visited, list):
                                    args = ', '.join(visited)
                                else:
                                    args = visited
                            nstr += "(" + args + ")"
                        case c_ast.PtrDecl():
                            if modifier.quals:
                                quals = " ".join(modifier.quals)
                                suffix = f" {nstr}" if nstr else ""
                                nstr = f"* {quals}{suffix}"
                            else:
                                nstr = "*" + nstr
                if nstr:
                    s += " " + nstr
                return s
            case c_ast.Decl():
                return self._generate_decl(n.type)
            case c_ast.Typename():
                return self._generate_type(n.type, emit_declname=emit_declname)
            case c_ast.IdentifierType():
                return " ".join(n.names) + " "
            case c_ast.ArrayDecl() | c_ast.PtrDecl() | c_ast.FuncDecl():
                return self._generate_type(
                    n.type, modifiers + [n], emit_declname=emit_declname
                )
            case _:
                return self.visit(n)

    def _parenthesize_if(
        self, n: c_ast.Node, condition: Callable[[c_ast.Node], bool]
    ) -> str:
        """Visits 'n' and returns its string representation, parenthesized
        if the condition function applied to the node returns True.
        """
        s = self._visit_expr(n)
        if condition(n):
            return "(" + s + ")"
        else:
            return s

    def _parenthesize_unless_simple(self, n: c_ast.Node) -> str:
        """Common use case for _parenthesize_if"""
        return self._parenthesize_if(n, lambda d: not self._is_simple_node(d))

    def _is_simple_node(self, n: c_ast.Node) -> bool:
        """Returns True for nodes that are "simple" - i.e. nodes that always
        have higher precedence than operators.
        """
        return isinstance(
            n,
            (c_ast.Constant, c_ast.ID, c_ast.ArrayRef, c_ast.StructRef, c_ast.FuncCall),
        )


class CGoalGenerator(CGenerator):
    """CGoal 代码生成器，继承自 CGenerator
    
    Args:
        filename: 源文件名（用于提取模块名）
        reduce_parentheses: 是否减少括号
        auto_namespace: 是否自动包装命名空间（默认True）
        namespace_prefix: 自定义命名空间前缀（默认None，使用文件名）
    """
    
    def __init__(self, filename: str = "<unknown>", reduce_parentheses: bool = False, 
                 auto_namespace: bool = True, namespace_prefix: str = None):
        super().__init__(reduce_parentheses)
        self.filename = filename
        self.module_name = os.path.splitext(os.path.basename(filename))[0]
        self.auto_namespace = auto_namespace
        self.namespace_prefix = namespace_prefix or self.module_name
        self._namespace_stack: List[str] = []
        self._class_names: set = set()
        self._class_fields: dict = {}
        self._symbols: dict = {}
        self._metadata: List[str] = []
        self._has_explicit_namespace = False
        self._var_types: dict = {}
        self._goal_impls: dict = {}
        self._goal_signatures: dict = {}
    
    def _visit_list(self, items) -> List[str]:
        """处理列表中的项，返回字符串列表"""
        if not items:
            return []
        if isinstance(items, list):
            return [self.visit(item) for item in items]
        return [self.visit(items)]
    
    def _mangle(self, name: str, is_main: bool = False) -> str:
        if is_main or name == 'main':
            return 'main'
        
        # 使用自定义前缀或模块名
        prefix = self.namespace_prefix.strip('<>')
        
        ns = '_'.join(self._namespace_stack)
        if ns:
            # 如果命名空间栈中的第一个元素等于前缀，说明是自动命名空间，避免重复
            if self._namespace_stack and self._namespace_stack[0] == prefix:
                if len(self._namespace_stack) == 1:
                    # 只有自动命名空间
                    return f"{prefix}_{name}"
                else:
                    # 有嵌套命名空间
                    ns_rest = '_'.join(self._namespace_stack[1:])
                    return f"{prefix}_{ns_rest}_{name}"
            else:
                return f"{prefix}_{ns}_{name}"
        return f"{prefix}_{name}"
    
    def _register_symbol(self, original: str):
        mangled = self._mangle(original)
        self._symbols[original] = mangled
        ns = '_'.join(self._namespace_stack) or "(global)"
        self._metadata.append(f"//@cgoal   {original}  ->  {mangled}")
    
    def import_symbols(self, symbols: dict):
        """导入外部符号映射
        
        Args:
            symbols: 符号映射字典，如 {'add': 'math_add', 'sub': 'math_sub'}
        """
        self._symbols.update(symbols)
    
    def import_metadata(self, metadata: dict):
        """从元数据字典导入符号
        
        Args:
            metadata: 元数据字典，包含 'symbols' 字段
        """
        if 'symbols' in metadata:
            self.import_symbols(metadata['symbols'])
    
    def _load_module_metadata(self, module_name: str) -> dict:
        """从同目录下的已编译文件中加载模块元数据
        
        Args:
            module_name: 模块名（如 'math'）
            
        Returns:
            元数据字典，包含 'symbols' 等字段
        """
        import os
        import re
        
        # 获取当前文件所在目录
        if self.filename and self.filename != "<unknown>":
            source_dir = os.path.dirname(os.path.abspath(self.filename))
        else:
            source_dir = os.getcwd()
        
        # 查找可能的文件：module.c, module.h
        possible_files = [
            os.path.join(source_dir, f"{module_name}.c"),
            os.path.join(source_dir, f"{module_name}.h")
        ]
        
        metadata = {'module': module_name, 'symbols': {}}
        
        for filepath in possible_files:
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 解析 //@cgoal 元数据
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('//@cgoal'):
                            # 解析符号映射: //@cgoal   add  ->  math_add
                            match = re.search(r'(\w+)\s*->\s*(\w+)', line)
                            if match:
                                symbol = match.group(1)
                                mangled = match.group(2)
                                metadata['symbols'][symbol] = mangled
                except Exception:
                    pass
        
        return metadata
    
    def _has_namespace_nodes(self, n: c_ast.FileAST) -> bool:
        """检查AST中是否有显式命名空间节点"""
        for ext in n.ext:
            if isinstance(ext, c_ast.Namespace):
                return True
            elif isinstance(ext, list):
                for item in ext:
                    if isinstance(item, c_ast.Namespace):
                        return True
        return False
    
    def visit_FileAST(self, n: c_ast.FileAST) -> str:
        self._metadata.append(f"//@cgoal module: {self.module_name}")
        
        has_explicit = self._has_namespace_nodes(n)
        
        if self.auto_namespace and not has_explicit:
            self._namespace_stack.append(self.namespace_prefix)
            self._metadata.append(f"//@cgoal namespace: {self.namespace_prefix} (auto)")
        
        result = []
        for ext in n.ext:
            if isinstance(ext, list):
                for item in ext:
                    visited = self.visit(item)
                    if isinstance(visited, list):
                        result.extend(visited)
                    else:
                        result.append(visited)
            else:
                visited = self.visit(ext)
                if isinstance(visited, list):
                    result.extend(visited)
                else:
                    # 为顶层声明添加分号（如果不是FuncDef、GoalBlock、StepBlock、ImplBlock、ClassDef、Namespace或Comment）
                    if not isinstance(ext, (c_ast.FuncDef, c_ast.GoalBlock, c_ast.StepBlock, c_ast.ImplBlock, c_ast.ClassDef, c_ast.Namespace, c_ast.Comment)):
                        result.append(visited + ';')
                    else:
                        result.append(visited)
        
        if self.auto_namespace and not has_explicit:
            self._namespace_stack.pop()
        
        return '\n'.join(self._metadata) + '\n' + '\n'.join(result)
    
    def visit_Namespace(self, n: c_ast.Namespace) -> str:
        self._has_explicit_namespace = True
        self._namespace_stack.append(n.name)
        self._metadata.append(f"//@cgoal namespace: {n.name}")
        
        result = []
        for decl in (n.decls or []):
            if isinstance(decl, list):
                for d in decl:
                    visited = self.visit(d)
                    if isinstance(visited, list):
                        result.extend(visited)
                    else:
                        # 为声明添加分号（如果不是函数定义、类定义、GoalBlock、StepBlock）
                        if not isinstance(d, (c_ast.FuncDef, c_ast.ClassDef, c_ast.GoalBlock, c_ast.StepBlock)):
                            result.append(visited + ';')
                        else:
                            result.append(visited)
            else:
                visited = self.visit(decl)
                if isinstance(visited, list):
                    result.extend(visited)
                else:
                    # 为声明添加分号（如果不是函数定义、类定义、GoalBlock、StepBlock）
                    if not isinstance(decl, (c_ast.FuncDef, c_ast.ClassDef, c_ast.GoalBlock, c_ast.StepBlock)):
                        result.append(visited + ';')
                    else:
                        result.append(visited)
        
        self._namespace_stack.pop()
        return '\n'.join(result)
    
    def visit_UsingDirective(self, n: c_ast.UsingDirective) -> str:
        if n.namespace:
            metadata = self._load_module_metadata(n.name)
            if metadata['symbols']:
                self.import_metadata(metadata)
        return ''
    
    def visit_ClassDef(self, n: c_ast.ClassDef) -> str:
        self._class_names.add(n.name)
        self._register_symbol(n.name)
        
        fields = []
        field_names = []
        for decl in (n.decls or []):
            if isinstance(decl, c_ast.Decl):
                field_names.append(decl.name)
                # 生成字段声明（类型 + 名称，带分号）
                field_str = self._generate_decl(decl)
                fields.append(field_str + ";")
        
        self._class_fields[n.name] = field_names
        
        result = ["typedef struct {"]
        for f in fields:
            result.append(f"    {f}")
        result.append(f"}} {n.name};")
        return '\n'.join(result)
    
    def visit_LetDecl(self, n: c_ast.LetDecl) -> str:
        name = n.name
        init = n.init
        
        # 判断是否为 class 类型
        is_class = False
        if n.type and hasattr(n.type, 'names'):
            if any(t in self._class_names for t in n.type.names):
                is_class = True
        
        # 构造函数调用
        if isinstance(init, c_ast.FuncCall) and isinstance(init.name, c_ast.ID):
            if init.name.name in self._class_names:
                is_class = True
                class_name = init.name.name
                
                # 记录变量类型为指针
                self._var_types[name] = ('pointer', class_name)
                
                # 生成 malloc + 字段初始化
                lines = [f"{class_name}* {name} = ({class_name}*)malloc(sizeof({class_name}));"]
                
                if init.args and class_name in self._class_fields:
                    field_names = self._class_fields[class_name]
                    for i, arg in enumerate(init.args.exprs):
                        if i < len(field_names):
                            lines.append(f"{name}->{field_names[i]} = {self.visit(arg)};")
                
                return '\n    '.join(lines)
        
        # 普通 let 声明
        if n.type:
            type_str = self.visit(n.type)
            # 记录变量类型
            if hasattr(n.type, 'names'):
                type_names = n.type.names
                if any(t in self._class_names for t in type_names):
                    self._var_types[name] = ('pointer', type_names[0])
                else:
                    self._var_types[name] = ('value', type_str)
        else:
            # 类型推断
            if isinstance(init, c_ast.Constant):
                if init.type == 'string':
                    type_str = 'char*'
                    self._var_types[name] = ('pointer', 'char')
                else:
                    type_str = 'int'
                    self._var_types[name] = ('value', 'int')
            else:
                type_str = 'int'
                self._var_types[name] = ('value', 'int')
        
        init_str = self._visit_expr(init) if init else ''
        return f"{type_str} {name} = {init_str};"
    
    def visit_GoalBlock(self, n: c_ast.GoalBlock) -> str:
        # 如果有 steps，说明是定义，否则是前向声明
        if n.steps:
            self._register_symbol(n.name)
            mangled = self._mangle(n.name)
            
            # 处理返回类型
            if n.outputs:
                if isinstance(n.outputs, list):
                    ret_type = ' '.join(self.visit(item) for item in n.outputs)
                else:
                    ret_type = self.visit(n.outputs)
            else:
                ret_type = 'void'
            
            # 处理参数列表
            params = []
            if n.inputs:
                if hasattr(n.inputs, 'params'):
                    for p in n.inputs.params:
                        visited = self.visit(p)
                        if isinstance(visited, list):
                            params.extend(visited)
                        else:
                            params.append(visited)
                elif isinstance(n.inputs, list):
                    for p in n.inputs:
                        visited = self.visit(p)
                        if isinstance(visited, list):
                            params.extend(visited)
                        else:
                            params.append(visited)
                else:
                    visited = self.visit(n.inputs)
                    if isinstance(visited, list):
                        params.extend(visited)
                    else:
                        params.append(visited)
            
            params_str = ', '.join(params) if params else 'void'
            
            # 记录 goal 签名（用于 impl）
            self._goal_signatures[n.name] = {
                'ret_type': ret_type,
                'params': params,
                'params_str': params_str
            }
            
            # 生成函数体（从 steps）
            body_lines = []
            if n.steps:
                for step in n.steps:
                    body_lines.append(self._generate_stmt(step))
            
            body = ''.join(body_lines)
            return f"{ret_type} {mangled}({params_str}) {{\n{body}}}"
        else:
            # 前向声明，记录 goal 名称
            if n.name not in self._goal_impls:
                self._goal_impls[n.name] = []
            return ''
    
    def visit_StepBlock(self, n: c_ast.StepBlock) -> str:
        self._register_symbol(n.name)
        mangled = self._mangle(n.name)
        
        # 处理返回类型
        if n.outputs:
            if isinstance(n.outputs, list):
                ret_type = ' '.join(self.visit(item) for item in n.outputs)
            else:
                ret_type = self.visit(n.outputs)
        else:
            ret_type = 'void'
        
        # 处理参数列表
        params = []
        if n.inputs:
            if hasattr(n.inputs, 'params'):
                for p in n.inputs.params:
                    visited = self.visit(p)
                    if isinstance(visited, list):
                        params.extend(visited)
                    else:
                        params.append(visited)
            elif isinstance(n.inputs, list):
                for p in n.inputs:
                    visited = self.visit(p)
                    if isinstance(visited, list):
                        params.extend(visited)
                    else:
                        params.append(visited)
            else:
                visited = self.visit(n.inputs)
                if isinstance(visited, list):
                    params.extend(visited)
                else:
                    params.append(visited)
        
        params_str = ', '.join(params) if params else 'void'
        
        body = self.visit(n.body) if n.body else ''
        if isinstance(body, list):
            body = '\n'.join(body)
        
        return f"{ret_type} {mangled}({params_str}) {body}"
    
    def visit_ImplBlock(self, n: c_ast.ImplBlock) -> str:
        # 记录 impl 实现
        goal_name = n.name
        strategy = n.target
        
        if goal_name not in self._goal_impls:
            self._goal_impls[goal_name] = []
        
        # 生成函数名：goal_strategy
        impl_func_name = f"{goal_name}_{strategy}"
        mangled = self._mangle(impl_func_name)
        
        # 注册符号
        self._register_symbol(impl_func_name)
        
        # 记录策略
        self._goal_impls[goal_name].append((strategy, mangled))
        
        # 从 goal 签名获取返回类型和参数
        signature = self._goal_signatures.get(goal_name, {
            'ret_type': 'void',
            'params_str': 'void'
        })
        ret_type = signature['ret_type']
        params_str = signature['params_str']
        
        if not n.body:
            return ''
        
        body = self.visit(n.body)
        if isinstance(body, list):
            body = '\n'.join(body)
        
        # 使用 goal 的签名生成函数
        return f"{ret_type} {mangled}({params_str}) {body}"
    
    def visit_AliasDef(self, n: c_ast.AliasDef) -> str:
        return f"// alias {n.name} = {n.value}"
    
    def visit_ExternCBlock(self, n: c_ast.ExternCBlock) -> str:
        result = ['extern "C" {']
        for decl in (n.decls or []):
            result.append(self.visit(decl))
        result.append('}')
        return '\n'.join(result)
    
    def visit_PipeExpr(self, n: c_ast.PipeExpr) -> str:
        left = self._visit_str(n.left)
        right = n.right
        
        # 如果右侧是函数调用，将左侧作为参数插入
        if isinstance(right, c_ast.FuncCall):
            func_name = self._visit_str(right.name)
            args = []
            if right.args:
                for arg in right.args.exprs:
                    args.append(self._visit_str(arg))
            args.insert(0, left)
            return f"{func_name}({', '.join(args)})"
        
        # 如果右侧是命名数据，返回左侧并赋值给命名数据
        if isinstance(right, c_ast.NamedData):
            return f"{right.name} = {left}"
        
        # 其他情况，返回顺序执行
        right_str = self._visit_str(right)
        return f"{left}; {right_str}"
    
    def visit_NamedData(self, n: c_ast.NamedData) -> str:
        return n.name
    
    def visit_ParallelExpr(self, n: c_ast.ParallelExpr) -> str:
        left = self.visit(n.left)
        right = self.visit(n.right)
        if isinstance(left, list):
            left = ' '.join(left)
        if isinstance(right, list):
            right = ' '.join(right)
        return f"/* parallel */ {left}, {right}"
    
    def visit_ConstructorCall(self, n: c_ast.ConstructorCall) -> str:
        return self.visit(n)
    
    def visit_IdentifierType(self, n: c_ast.IdentifierType) -> str:
        names = ['char*' if name == 'string' else name for name in n.names]
        return ' '.join(names)
    
    def visit_ID(self, n: c_ast.ID) -> str:
        if n.name in self._symbols:
            return self._symbols[n.name]
        return n.name
    
    def visit_StructRef(self, n: c_ast.StructRef) -> str:
        if n.type == '::':
            # 获取命名空间名称（不进行符号查找）
            if isinstance(n.name, c_ast.ID):
                ns_name = n.name.name
            else:
                ns_name = self.visit(n.name)
                if isinstance(ns_name, list):
                    ns_name = '_'.join(ns_name)
            
            # 获取函数名（不进行符号查找）
            if isinstance(n.field, c_ast.ID):
                func_name = n.field.name
            else:
                func_name = self.visit(n.field)
                if isinstance(func_name, list):
                    func_name = '_'.join(func_name)
            
            # 拼接成完整名称
            full_name = f"{ns_name}_{func_name}"
            
            # 在符号表中查找
            if full_name in self._symbols:
                return self._symbols[full_name]
            
            # 否则进行 mangle
            return self._mangle(full_name)
        
        # 成员访问自动转换
        # 检查左侧是否是变量名
        if isinstance(n.name, c_ast.ID):
            var_name = n.name.name
            if var_name in self._var_types:
                var_type_info = self._var_types[var_name]
                # 如果是指针类型，使用 ->
                if var_type_info[0] == 'pointer':
                    sref = self._parenthesize_unless_simple(n.name)
                    if isinstance(sref, list):
                        sref = ''.join(sref)
                    field = self.visit(n.field)
                    if isinstance(field, list):
                        field = ''.join(field)
                    return sref + '->' + field
        
        # 调用父类方法，但确保返回字符串
        sref = self._parenthesize_unless_simple(n.name)
        if isinstance(sref, list):
            sref = ''.join(sref)
        field = self.visit(n.field)
        if isinstance(field, list):
            field = ''.join(field)
        return sref + n.type + field
    
    def visit_FuncDef(self, n: c_ast.FuncDef) -> str:
        decl = n.decl
        is_main = decl.name == 'main'
        is_extern = 'extern' in (decl.storage or [])
        is_static = 'static' in (decl.storage or [])
        
        if not is_main and not is_extern and not is_static:
            self._register_symbol(decl.name)
            mangled = self._mangle(decl.name)
            
            # 生成函数定义，手动处理名称修饰
            parts = []
            
            # 生成声明说明符
            if decl.funcspec:
                parts.append(' '.join(decl.funcspec))
            
            # 生成类型和修饰后的名称
            type_str = self._generate_type(decl.type)
            # 替换函数名为修饰后的名称
            type_str = type_str.replace(decl.name, mangled, 1)
            parts.append(type_str)
            
            # 生成 K&R 参数声明
            if n.param_decls:
                for param in n.param_decls:
                    visited = self.visit(param)
                    if isinstance(visited, list):
                        parts.append('; '.join(visited) + ';')
                    else:
                        parts.append(visited + ';')
            
            # 生成函数体
            body = self.visit(n.body)
            if isinstance(body, list):
                body = '\n'.join(body)
            parts.append(body)
            
            return '\n'.join(parts)
        
        return super().visit_FuncDef(n)

import os