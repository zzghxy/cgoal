#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGoal 编译器 - 将 CGoal 语言编译为 C 代码

CGoal 是 C 语言的超集，提供现代语法、命名空间和 Goal 范式。
本编译器将 .cgoal 文件转换为标准 C 代码，可直接用 GCC/Clang 编译。

用法:
    cgoalc <source.cgoal>              # 生成 C 代码
    cgoalc <source.cgoal> --compile    # 生成并编译
    cgoalc <source.cgoal> --run        # 生成、编译并运行
    cgoalc --project <dir>             # 编译整个项目
    cgoalc --clean <dir>               # 清理生成的文件

版本: 1.0.0
作者: CGoal Team
"""

import sys
import os
import argparse
import subprocess
import shutil
import json
from pathlib import Path
from typing import List, Optional, Dict
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser.c_parser import CParser
from parser.c_generator import CGoalGenerator
from preprocessor.preprocessor import Preprocessor


__version__ = '1.0.0'
__author__ = 'CGoal Team'


class CompileError(Exception):
    """编译错误"""
    pass


class CGoalCompiler:
    """CGoal 编译器核心类"""
    
    def __init__(self, verbose: bool = False, color: bool = True):
        self.verbose = verbose
        self.color = color
        self.parser = CParser()
        self.stats = {
            'files_processed': 0,
            'lines_processed': 0,
            'errors': 0,
            'warnings': 0
        }
    
    def compile_file(
        self,
        input_path: str,
        output_dir: Optional[str] = None,
        compile_c: bool = False,
        run_program: bool = False,
        keep_c: bool = True,
        auto_namespace: bool = True,
        namespace_prefix: Optional[str] = None
    ) -> str:
        """
        编译单个 CGoal 文件
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            compile_c: 是否编译为可执行文件
            run_program: 是否运行程序
            keep_c: 是否保留生成的 C 文件
            auto_namespace: 是否自动包装命名空间
            namespace_prefix: 自定义命名空间前缀
            
        Returns:
            生成的 C 文件路径
        """
        input_path = os.path.abspath(input_path)
        
        # 验证输入文件
        self._validate_input_file(input_path)
        
        # 准备输出路径
        module_name = os.path.splitext(os.path.basename(input_path))[0]
        base_dir = os.path.dirname(input_path)
        output_dir = os.path.abspath(output_dir) if output_dir else base_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self._log(f"编译文件: {input_path}", color='cyan')
        self._log(f"模块名: {module_name}", color='blue')
        
        try:
            # 1. 读取源文件
            self._log("[1/5] 读取源文件...", color='yellow')
            source = self._read_source(input_path)
            self.stats['lines_processed'] += source.count('\n')
            
            # 2. 预处理
            self._log("[2/5] 预处理...", color='yellow')
            preprocessed = self._preprocess_source(source, input_path)
            
            # 3. 解析为 AST
            self._log("[3/5] 解析为 AST...", color='yellow')
            ast = self._parse_source(preprocessed, input_path)
            
            # 4. 生成 C 代码
            self._log("[4/5] 生成 C 代码...", color='yellow')
            c_code = self._generate_c_code(ast, input_path, auto_namespace, namespace_prefix)
            
            # 5. 写入文件
            self._log("[5/5] 写入文件...", color='yellow')
            c_path = self._write_c_file(c_code, output_dir, module_name)
            
            self.stats['files_processed'] += 1
            self._log(f"✓ 生成: {c_path}", color='green')
            
            # 5. 可选：编译 C 代码
            if compile_c:
                exe_path = self._compile_c_code(c_path, output_dir, module_name)
                
                # 6. 可选：运行程序
                if run_program:
                    self._run_program(exe_path)
            
            # 7. 可选：清理 C 文件
            if not keep_c and compile_c:
                os.remove(c_path)
                self._log(f"清理: {c_path}", color='yellow')
            
            return c_path
            
        except Exception as e:
            self.stats['errors'] += 1
            self._error(f"编译失败: {e}")
            raise CompileError(str(e))
    
    def compile_project(
        self,
        project_dir: str,
        output_dir: Optional[str] = None,
        compile_c: bool = False,
        run_program: bool = False
    ) -> List[str]:
        """
        编译整个项目
        
        Args:
            project_dir: 项目目录
            output_dir: 输出目录
            compile_c: 是否编译为可执行文件
            run_program: 是否运行程序
            
        Returns:
            生成的 C 文件列表
        """
        project_dir = os.path.abspath(project_dir)
        
        if not os.path.isdir(project_dir):
            raise CompileError(f"项目目录不存在: {project_dir}")
        
        self._log(f"编译项目: {project_dir}", color='cyan')
        
        # 查找所有 .cgoal 文件
        cgoal_files = self._find_cgoal_files(project_dir)
        
        if not cgoal_files:
            self._log("未找到 .cgoal 文件", color='yellow')
            return []
        
        self._log(f"找到 {len(cgoal_files)} 个文件", color='blue')
        
        # 编译每个文件
        generated_files = []
        for cgoal_file in cgoal_files:
            try:
                c_file = self.compile_file(
                    cgoal_file,
                    output_dir,
                    compile_c=False,
                    run_program=False
                )
                generated_files.append(c_file)
            except CompileError as e:
                self._error(f"跳过文件: {cgoal_file}")
                continue
        
        # 如果需要编译，编译整个项目
        if compile_c and generated_files:
            self._compile_project(generated_files, output_dir, run_program)
        
        return generated_files
    
    def clean(self, directory: str) -> None:
        """
        清理生成的文件
        
        Args:
            directory: 要清理的目录
        """
        directory = os.path.abspath(directory)
        
        if not os.path.isdir(directory):
            self._log(f"目录不存在: {directory}", color='yellow')
            return
        
        self._log(f"清理目录: {directory}", color='cyan')
        
        # 清理 .c, .h, .exe 文件
        patterns = ['*.c', '*.h', '*.exe', '*.o', '*.obj']
        cleaned = 0
        
        for pattern in patterns:
            for file_path in Path(directory).glob(pattern):
                # 跳过 .cgoal 文件
                if file_path.suffix == '.cgoal':
                    continue
                
                try:
                    os.remove(file_path)
                    self._log(f"删除: {file_path}", color='yellow')
                    cleaned += 1
                except Exception as e:
                    self._error(f"删除失败: {file_path}: {e}")
        
        self._log(f"清理完成: 删除了 {cleaned} 个文件", color='green')
    
    def _validate_input_file(self, input_path: str) -> None:
        """验证输入文件"""
        if not os.path.exists(input_path):
            raise CompileError(f"源文件不存在: {input_path}")
        
        if not input_path.endswith('.cgoal'):
            raise CompileError(f"源文件必须是 .cgoal 文件: {input_path}")
    
    def _read_source(self, input_path: str) -> str:
        """读取源文件"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise CompileError(f"读取文件失败: {e}")
    
    def _preprocess_source(self, source: str, filename: str) -> str:
        """预处理源代码（处理预处理器指令）"""
        try:
            pp = Preprocessor()
            
            # 添加当前文件所在目录到包含路径
            file_dir = os.path.dirname(os.path.abspath(filename))
            pp.add_path(file_dir)
            
            # 添加项目根目录到包含路径
            project_dir = os.path.dirname(file_dir)
            pp.add_path(project_dir)
            
            # 预处理
            import io
            output = io.StringIO()
            pp.parse(source)
            pp.write(output)
            
            return output.getvalue()
        except Exception as e:
            self._log(f"预处理警告: {e}", color='yellow')
            return source
    
    def _parse_source(self, source: str, filename: str):
        """解析源代码"""
        try:
            return self.parser.parse(source, filename=filename)
        except Exception as e:
            raise CompileError(f"解析失败: {e}")
    
    def _generate_c_code(
        self,
        ast,
        filename: str,
        auto_namespace: bool = True,
        namespace_prefix: Optional[str] = None
    ) -> str:
        """生成 C 代码"""
        try:
            generator = CGoalGenerator(
                filename=filename,
                auto_namespace=auto_namespace,
                namespace_prefix=namespace_prefix
            )
            return generator.visit(ast)
        except Exception as e:
            raise CompileError(f"代码生成失败: {e}")
    
    def _write_c_file(self, c_code: str, output_dir: str, module_name: str) -> str:
        """写入 C 文件"""
        c_path = os.path.join(output_dir, f"{module_name}.c")
        
        try:
            with open(c_path, 'w', encoding='utf-8') as f:
                f.write(c_code)
            return c_path
        except Exception as e:
            raise CompileError(f"写入文件失败: {e}")
    
    def _compile_c_code(self, c_path: str, output_dir: str, module_name: str) -> str:
        """编译 C 代码"""
        self._log("[5/5] 编译 C 代码...", color='yellow')
        
        compiler = self._find_c_compiler()
        exe_name = f"{module_name}.exe" if sys.platform == 'win32' else module_name
        exe_path = os.path.join(output_dir, exe_name)
        
        cmd = [
            compiler,
            '-std=c11',
            '-O2',
            '-Wall',
            '-o', exe_path,
            c_path
        ]
        
        self._log(f"执行: {' '.join(cmd)}", color='blue')
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self._error("编译失败:")
                self._error(result.stderr)
                raise CompileError("C 编译失败")
            
            self._log(f"✓ 编译: {exe_path}", color='green')
            
            if result.stdout:
                print(result.stdout)
            
            return exe_path
            
        except FileNotFoundError:
            raise CompileError(f"编译器未找到: {compiler}")
        except Exception as e:
            raise CompileError(f"编译失败: {e}")
    
    def _run_program(self, exe_path: str) -> None:
        """运行程序"""
        if not os.path.exists(exe_path):
            raise CompileError(f"可执行文件不存在: {exe_path}")
        
        self._log(f"\n运行程序: {exe_path}", color='cyan')
        print("=" * 60)
        
        try:
            result = subprocess.run(
                [exe_path],
                cwd=os.path.dirname(exe_path),
                capture_output=False
            )
            
            print("=" * 60)
            self._log(f"程序退出码: {result.returncode}", color='blue')
            
        except Exception as e:
            raise CompileError(f"运行失败: {e}")
    
    def _compile_project(self, c_files: List[str], output_dir: str, run: bool) -> None:
        """编译整个项目"""
        self._log("编译项目...", color='yellow')
        
        compiler = self._find_c_compiler()
        exe_name = 'main.exe' if sys.platform == 'win32' else 'main'
        exe_path = os.path.join(output_dir, exe_name)
        
        cmd = [compiler, '-std=c11', '-O2', '-Wall', '-o', exe_path] + c_files
        
        self._log(f"执行: {' '.join(cmd)}", color='blue')
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self._error("项目编译失败:")
                self._error(result.stderr)
                raise CompileError("项目编译失败")
            
            self._log(f"✓ 项目编译成功: {exe_path}", color='green')
            
            if run:
                self._run_program(exe_path)
                
        except Exception as e:
            raise CompileError(f"项目编译失败: {e}")
    
    def _find_c_compiler(self) -> str:
        """查找 C 编译器"""
        for compiler in ['gcc', 'clang', 'cl']:
            if shutil.which(compiler):
                return compiler
        
        raise CompileError("未找到 C 编译器 (需要 gcc/clang/msvc)")
    
    def _find_cgoal_files(self, directory: str) -> List[str]:
        """查找所有 .cgoal 文件"""
        cgoal_files = []
        
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和构建目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['build', 'dist', '__pycache__']]
            
            for file in files:
                if file.endswith('.cgoal'):
                    cgoal_files.append(os.path.join(root, file))
        
        return sorted(cgoal_files)
    
    def _log(self, message: str, color: str = None) -> None:
        """打印日志"""
        if not self.verbose:
            return
        
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'white': '\033[97m',
        }
        
        if self.color and color and color in colors:
            print(f"{colors[color]}{message}\033[0m")
        else:
            print(message)
    
    def _error(self, message: str) -> None:
        """打印错误"""
        self.stats['errors'] += 1
        
        if self.color:
            print(f"\033[91m错误: {message}\033[0m", file=sys.stderr)
        else:
            print(f"错误: {message}", file=sys.stderr)
    
    def print_stats(self) -> None:
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("编译统计:")
        print(f"  处理文件: {self.stats['files_processed']}")
        print(f"  处理行数: {self.stats['lines_processed']}")
        print(f"  错误数: {self.stats['errors']}")
        print(f"  警告数: {self.stats['warnings']}")
        print("=" * 60)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='cgoalc',
        description='CGoal 编译器 - 将 CGoal 语言编译为 C 代码',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成 C 代码
  cgoalc hello.cgoal
  
  # 生成并编译
  cgoalc hello.cgoal --compile
  
  # 生成、编译并运行
  cgoalc hello.cgoal --compile --run
  
  # 编译整个项目
  cgoalc --project ./src
  
  # 清理生成的文件
  cgoalc --clean ./build
  
  # 显示详细信息
  cgoalc hello.cgoal -v

更多信息请访问: https://github.com/cgoal/cgoal
        """
    )
    
    # 位置参数
    parser.add_argument(
        'source',
        nargs='?',
        help='CGoal 源文件 (.cgoal)'
    )
    
    # 可选参数
    parser.add_argument(
        '-o', '--output',
        help='输出目录'
    )
    
    parser.add_argument(
        '-c', '--compile',
        action='store_true',
        help='编译生成的 C 代码'
    )
    
    parser.add_argument(
        '-r', '--run',
        action='store_true',
        help='运行生成的程序（需要 --compile）'
    )
    
    parser.add_argument(
        '--keep-c',
        action='store_true',
        default=True,
        help='保留生成的 C 文件（默认）'
    )
    
    parser.add_argument(
        '--no-keep-c',
        action='store_false',
        dest='keep_c',
        help='不保留生成的 C 文件'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细信息'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='禁用彩色输出'
    )
    
    parser.add_argument(
        '--no-namespace',
        action='store_true',
        help='禁用自动命名空间包装'
    )
    
    parser.add_argument(
        '--namespace-prefix',
        metavar='PREFIX',
        help='自定义命名空间前缀（默认使用文件名）'
    )
    
    # 项目模式
    parser.add_argument(
        '--project',
        metavar='DIR',
        help='编译整个项目'
    )
    
    # 清理模式
    parser.add_argument(
        '--clean',
        metavar='DIR',
        help='清理生成的文件'
    )
    
    # 版本信息
    parser.add_argument(
        '--version',
        action='version',
        version=f'CGoal 编译器 v{__version__}'
    )
    
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 显示帮助
    if not args.source and not args.project and not args.clean:
        parser.print_help()
        sys.exit(0)
    
    # 创建编译器
    compiler = CGoalCompiler(
        verbose=args.verbose,
        color=not args.no_color
    )
    
    try:
        start_time = time.time()
        
        # 清理模式
        if args.clean:
            compiler.clean(args.clean)
        
        # 项目模式
        elif args.project:
            compiler.compile_project(
                args.project,
                args.output,
                args.compile,
                args.run
            )
        
        # 单文件模式
        elif args.source:
            compiler.compile_file(
                args.source,
                args.output,
                args.compile,
                args.run,
                args.keep_c
            )
        
        # 打印统计信息
        if args.verbose:
            elapsed = time.time() - start_time
            print(f"\n编译耗时: {elapsed:.2f} 秒")
            compiler.print_stats()
        
    except CompileError as e:
        print(f"\n编译错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n未知错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()