# CGoal
A C superset language with goal-oriented programming, namespaces, and classes
<div align="center">

**A C programming language superset with goal-oriented features, namespaces, and classes**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/zzghxy/cgoal)

[English](#english) | [中文](#中文)

</div>

---

## English

### Overview

CGoal is a modern programming language that extends C with powerful features while maintaining full compatibility with existing C code. It introduces:

- **Goal-Oriented Programming**: Declarative data flow orchestration with zero runtime overhead
- **Namespaces**: Organize code with hierarchical namespaces
- **Classes**: Object-oriented programming with automatic memory management
- **Modern Syntax**: Simplified variable declarations and type inference

### Key Features

✨ **C Superset**: All valid C code (C89/C99/C11) is valid CGoal code  
🎯 **Goal Paradigm**: Declarative step-by-step execution with pipe operators (`|>`)  
📦 **Namespaces**: Hierarchical code organization and modular design  
🏗️ **Classes**: Reference semantics with automatic garbage collection  
🚀 **Zero Runtime**: Compiles to standard C, works with any C compiler  
💡 **Type Inference**: Automatic type deduction with `let` keyword  

### Quick Start

#### Installation

**Option 1: Use Pre-built Binary (Windows)**
```bash
# Download cgoalc.exe from releases
cgoalc hello.cgoal
```

**Option 2: Build from Source**
```bash
# Clone the repository
git clone https://github.com/zzghxy/cgoal.git
cd cgoal



# Run the compiler
python cgoalc.py filename.cgoal
```

#### Basic Usage

```bash
# Generate C code
cgoalc hello.cgoal

# Generate and compile
cgoalc hello.cgoal --compile

# Generate, compile and run
cgoalc hello.cgoal --compile --run

# Compile entire project
cgoalc --project ./src

# Clean generated files
cgoalc --clean ./build
```

### CGoal Language Features

#### 1. Variable Declaration with `let`

```cgoal
// Type inference
let x = 5;                    // int x = 5;
let name = "Alice";           // char* name = "Alice";

// Explicit type
let age: int = 25;            // int age = 25;
```

#### 2. Class Definition

```cgoal
class Person {
    string name;
    int age;
}

// Create instance
let p = Person("Alice", 25);
```

#### 3. Namespaces

```cgoal
namespace MyApp.Models {
    class User {
        string username;
        int id;
    }
}

// Using namespace
using MyApp.Models;
let user = User("john_doe", 1);
```

#### 4. Goal-Oriented Programming

```cgoal
goal int process() {
    step load_data() |> 
    step validate() |> 
    step transform() |> 
    step save()
}
```

### Project Structure

```
cgoal/
├── parser/              # Parser and AST implementation
│   ├── c_parser.py     # CGoal parser
│   ├── c_lexer.py      # Lexer
│   ├── c_ast.py        # AST node definitions
│   └── c_generator.py  # C code generator
├── preprocessor/        # Preprocessor implementation
│   └── preprocessor.py # CGoal preprocessor
├── examples/            # Example programs
│   ├── hello.cgoal     # Hello World
│   └── complete_test.cgoal
├── test/                # Test suite
├── README/              # Documentation
│   └── CGoal语言手册.md
├── cgoalc.py           # Main compiler entry point
├── build_exe.py        # Build script for executable
└── BUILD.md            # Build instructions
```

### Building Executable

Build a standalone executable with PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Build
python build_exe.py

# Output: dist/cgoalc.exe
```

### Examples

Check the `examples/` directory for more examples:

- `hello.cgoal` - Basic Hello World
- `complete_test.cgoal` - Comprehensive feature demonstration

### Contributing

We welcome contributions! Please see our contributing guidelines for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 中文

### 概述

CGoal 是一种现代编程语言，在保持与现有 C 代码完全兼容的同时，扩展了 C 语言的功能。它引入了：

- **面向目标编程**：声明式数据流编排，零运行时开销
- **命名空间**：通过层次化命名空间组织代码
- **类定义**：具有自动内存管理的面向对象编程
- **现代语法**：简化的变量声明和类型推断

### 核心特性

✨ **C 超集**：所有合法的 C 代码（C89/C99/C11）都是合法的 CGoal 代码  
🎯 **Goal 范式**：通过管道操作符（`|>`）实现声明式步骤执行  
📦 **命名空间**：层次化代码组织和模块化设计  
🏗️ **类定义**：引用语义与自动垃圾回收  
🚀 **零运行时**：编译为标准 C 代码，可与任何 C 编译器配合使用  
💡 **类型推断**：使用 `let` 关键字自动推导类型  

### 快速开始

#### 安装

**方式一：使用预编译二进制文件（Windows）**
```bash
# 从 releases 下载 cgoalc.exe
cgoalc hello.cgoal
```

**方式二：从源码构建**
```bash
# 克隆仓库
git clone https://github.com/zzghxy/cgoal.git
cd cgoal



# 运行编译器
python cgoalc.py filename.cgoal
```

#### 基本用法

```bash
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
```

### CGoal 语言特性

#### 1. 使用 `let` 声明变量

```cgoal
// 类型推断
let x = 5;                    // int x = 5;
let name = "Alice";           // char* name = "Alice";

// 显式类型
let age: int = 25;            // int age = 25;
```

#### 2. 类定义

```cgoal
class Person {
    string name;
    int age;
}

// 创建实例
let p = Person("Alice", 25);
```

#### 3. 命名空间

```cgoal
namespace MyApp.Models {
    class User {
        string username;
        int id;
    }
}

// 使用命名空间
using MyApp.Models;
let user = User("john_doe", 1);
```

#### 4. 面向目标编程

```cgoal
goal int process() {
    step load_data() |> 
    step validate() |> 
    step transform() |> 
    step save()
}
```

### 项目结构

```
cgoal/
├── parser/              # 解析器和 AST 实现
│   ├── c_parser.py     # CGoal 解析器
│   ├── c_lexer.py      # 词法分析器
│   ├── c_ast.py        # AST 节点定义
│   └── c_generator.py  # C 代码生成器
├── preprocessor/        # 预处理器实现
│   └── preprocessor.py # CGoal 预处理器
├── examples/            # 示例程序
│   ├── hello.cgoal     # Hello World
│   └── complete_test.cgoal
├── test/                # 测试套件
├── README/              # 文档
│   └── CGoal语言手册.md
├── cgoalc.py           # 主编译器入口
├── build_exe.py        # 可执行文件构建脚本
└── BUILD.md            # 构建说明
```

### 构建可执行文件

使用 PyInstaller 构建独立可执行文件：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 构建
python build_exe.py

# 输出: dist/cgoalc.exe
```

### 示例

查看 `examples/` 目录获取更多示例：

- `hello.cgoal` - 基础 Hello World
- `complete_test.cgoal` - 综合特性演示

### 贡献

我们欢迎贡献！请查看我们的贡献指南了解详情。

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

### 许可证

本项目采用 Apache License 2.0 许可证 - 详情请查看 [LICENSE](LICENSE) 文件。

---

## Documentation

For comprehensive documentation, see:
- [CGoal Language Manual](README/CGoal语言手册.md) (Chinese)
- [Build Instructions](BUILD.md)

## Support

- 📖 [Documentation](README/CGoal语言手册.md)
- 🐛 [Issue Tracker](https://github.com/yourusername/cgoal/issues)
- 💬 [Discussions](https://github.com/yourusername/cgoal/discussions)

## Roadmap

- [ ] Add more comprehensive standard library
- [ ] IDE extensions (VSCode, Vim)
- [ ] Package manager integration
- [ ] Cross-platform binary releases
- [ ] Interactive documentation website

## Acknowledgments

- Built with [PLY (Python Lex-Yacc)](https://www.dabeaz.com/ply/)
- Preprocessor powered by [pcpp](https://github.com/ned14/pcpp)
- Inspired by modern programming language design

---

<div align="center">

**Made with ❤️ by the CGoal Team**

[⬆ Back to Top](#cgoal)

</div>
