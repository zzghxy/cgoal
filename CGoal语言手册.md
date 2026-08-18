# CGoal 语言手册

[English](#cgoal-language-manual-english) | 中文

> **版本**：1.0  


---

## 1. 概述

CGoal 是 C 语言的超集，在标准 C 基础上增加了**现代语法**、**命名空间与模块化**以及**声明式数据流编排（Goal 范式）**。CGoal 源文件通过 `cgoal` 转换器编译为同名的标准 C 文件（`.c` / `.h`）。

### 设计目标

- **C 超集**：所有合法的 C 代码（C89/C99）都是 CGoal 的合法代码。
- **现代语法**：提供更简洁的变量声明、类定义和自动内存管理（还未实现）。
- **自动内存管理**：`class` 类型的对象默认由垃圾回收管理，用户无需手动释放。
- **引用语义**：`class` 对象默认按引用传递，赋值即共享。
- **Goal 范式**：声明式数据流编排，通过管道（`|>`）串联步骤，编译期展开，零运行时开销。
- **转换产物即标准 C**：无需额外运行时，可直接用 GCC/Clang 编译链接。

### 文件后缀

| 类型 | 后缀 |
|------|------|
| CGoal 源文件 | `.cgoal` |
| CGoal 头文件 | `.hgoal` |
| 输出 C 文件 | `.c` |
| 输出头文件 | `.h` |

---

## 2. 基础扩展语法

### 2.1 变量声明：`let`

**语法形式**：
```cgoal
let name: type = initializer;   // 显式类型
let name = initializer;         // 类型推断（可选）
```

**语义**：
- 声明一个变量，作用域从声明处开始到当前块结束。
- **`let` 声明的变量默认为指针**，特别是当类型为 `class` 定义的类时，变量为指向堆上对象的指针，由 GC 管理。
- 对于 C 基本类型（`int`、`float`、`char` 等）或普通 `struct`，`let` 变量仍为**值类型**（栈上分配），以保持与 C 的完全兼容。
- 如果初始化器是一个构造函数调用（如 `Person(...)`），编译器自动推断为指针类型。

**转译目标（C 代码）**：
- 引用类型（`class`）：生成指针声明 + 堆分配。
- 值类型：生成普通 C 声明。

**示例**：
```cgoal
let x: int = 5;               // 值类型 → int x = 5;
let name: string = "Alice";   // string 映射为 char* → char* name = "Alice";
let p = Person("Alice", 25);  // 引用类型 → Person* p = ...
```

---

### 2.2 类定义：`class`

**语法形式**：
```cgoal
class Person {
    string name;
    int age;
}
```

**字段声明语法**：
```
类型 字段名;
```

字段声明与 C 结构体字段**完全一致**：类型在前，字段名在后。字段可以是任意合法 C 类型（基本类型、指针、结构体、`string` 等）。

**语义**：
- 定义一个类类型，底层对应一个 C 结构体。
- 所有该类的变量都是引用（指针），赋值共享对象。
- 支持 `ClassName(arg1, arg2, ...)` 语法创建对象。
- 字段按声明顺序排列。

**转译目标（C 代码）**：
```c
typedef struct {
    char* name;
    int age;
} Person;
```

**规则**：
- `string` 类型映射为 `char*`。
- 字段语法与 C 结构体完全相同，不引入新的字段声明顺序。

---

### 2.3 构造函数调用

**语法形式**：
```cgoal
let p = Person("Alice", 25);
```

**语义**：
- 创建一个该类的新对象（堆分配），按参数顺序初始化字段。
- 参数个数必须与字段个数相同。

**转译目标（C 代码）**：
```c
Person* p = (Person*)GC_malloc(sizeof(Person));
p->name = "Alice";
p->age = 25;
```

---

### 2.4 成员访问

**语法形式**：
```cgoal
p.age = 26;
printf("%d\n", p.age);
```

**语义**：
- 无论变量是值还是引用，统一使用 `.` 访问成员。
- 编译器自动决定底层使用 `.` 还是 `->`。

**转译规则**：
- 值类型 → `变量.成员`
- 引用类型（指针）→ `变量->成员`

---

### 2.5 内置类型

- **`string`**：映射为 `char*`。

（不提供内置输出函数，所有输出通过标准 C `printf` 完成，用户自行指定格式符。）

---

## 3. 命名空间与链接规范

### 3.1 命名空间定义

**语法形式**：
```cgoal
namespace 标识符 {
    // 变量、函数、类型、结构体定义...
}
```

**语义**：
- 定义命名空间，用于避免全局符号冲突和提供语义分组。
- 支持嵌套命名空间。
- 使用 `::` 访问命名空间成员。

**示例**：
```cgoal
namespace MyLib {
    int version = 1;
    void hello() { ... }
}

int main() {
    MyLib::hello();
    int v = MyLib::version;
    return 0;
}
```

**转译目标（C 代码）**：
- 命名空间内的符号进行名称修饰，例如 `MyLib::hello` 变为 `MyLib_hello`。
- 修饰规则：`命名空间名_符号名`，嵌套时用 `_` 连接。

---

### 3.2 文件级自动命名空间包装

**规则**：编译器在加载主源文件时，自动将其内容包裹在 `namespace <文件名> { ... }` 中。

**效果**：
- 文件内所有全局符号自动归属于以文件名命名的命名空间。
- 避免多个源文件之间的符号冲突。
- 用户显式定义的命名空间嵌套在自动命名空间之内。

**示例**：
用户源码 `main.cgoal`：
```cgoal
int global_var = 100;
void foo() { ... }
```
编译器实际处理：
```cgoal
namespace main {
    int global_var = 100;
    void foo() { ... }
}
```

---

### 3.3 命名修饰规则总结

```
完整修饰名 = filename + "_" + [namespace + "_"]* + APIname

示例:
  math.cgoal, namespace Math, add()   → math_Math_add
  math.cgoal, namespace A::B, foo()   → math_A_B_foo
  math.cgoal, 顶层, init()            → math_init
  app.cgoal, 顶层, main()             → main
```

### 3.4 不添加前缀的情况

| 情况 | 说明 |
|------|------|
| `static` 函数/变量 | 已限制在翻译单元内，无需前缀 |
| `main()` 函数 | C 运行时入口，必须保留原名 |
| `#include` 引入的符号 | 属于外部头文件的标准 C 符号 |
| 局部变量 | 作用域在函数内，无冲突风险 |

---

### 3.5 `extern "C"` 链接规范

**语法形式**：
```cgoal
extern "C" {
    // 函数声明或定义
}
// 或单个声明
extern "C" void printf(const char* format, ...);
```

**语义**：
- 在 `extern "C"` 块内声明的所有函数和全局变量，关闭名称修饰。
- 生成的符号名与纯 C 编译结果一致。
- 用于与标准 C 库及操作系统 API 互操作。

**示例**：
```cgoal
extern "C" {
    #include <stdio.h>
}
```

---

### 3.6 `using` 指令与声明

#### `using` 指令

```cgoal
using namespace <name>;
```

将命名空间 `<name>` 中的**所有符号**导入当前作用域。

- 可以出现在任何 C 作用域内（函数体、命名空间体、文件顶层）
- 转换时，被导入的符号替换为其全限定名

**示例**：
```cgoal
// app.cgoal
using namespace Math;

int main() {
    int r = add(1, 2);    // → math_Math_add(1, 2)
    int s = sub(5, 3);    // → math_Math_sub(5, 3)
    return 0;
}
```

#### `using` 声明

```cgoal
using <namespace>::<symbol>;
```

仅导入指定符号，而非整个命名空间。

```cgoal
using Math::add;   // 只导入 add

int main() {
    int r = add(1, 2);    // → math_Math_add(1, 2)
    // sub(5, 3);         // 错误：sub 未导入
    return 0;
}
```

#### 名称冲突处理

若两条 `using` 指令引入同名符号，编译报错（歧义）：

```cgoal
using namespace Math;    // 导出 add
using namespace Utils;   // 也导出 add
// add(1, 2);            // 歧义！编译报错
```

此时必须用显式声明消歧：

```cgoal
using Math::add;         // 明确指定
```

#### 嵌套 `using` 不传递

```cgoal
// A.cgoal
namespace A {
    using namespace B;   // 仅 A 内部可见 B 的符号
    int x = B_foo;       // 正确
}

// app.cgoal
using namespace A;
// B_foo;                // 错误：B 的符号不传递
```

#### 与 C++ 的差异

| 特性 | C++ | CGoal |
|------|-----|-------|
| `using namespace` 在头文件 | 反模式 | 安全（文件级命名空间隔离） |
| `using` 导入类型 | 支持 `class`/`enum` | 仅限变量和函数 |
| `using` 类型别名 | `using Foo = int;` | 不支持 |
| 冲突解析 | 更特化者优先 | 直接报错，要求显式消歧 |

---

### 3.7 跨文件符号解析

#### 基本原理

CGoal 转换器读取同目录下已有的 `.c` / `.h` 文件，从中提取 `//@cgoal` 元数据行来解析 `using` 指令的外部符号。

#### 元数据注释格式

每个输出的 `.c` 和 `.h` 文件头部包含元数据：

```c
//@cgoal module: math
//@cgoal namespace: Math
//@cgoal   add  ->  math_Math_add
//@cgoal   sub  ->  math_Math_sub
//@cgoal namespace: (global)
//@cgoal   init  ->  math_init
```

#### 转换器解析流程

```
cgoal app.cgoal

  1. 解析 app.cgoal
  2. 发现 "using namespace Math;"
  3. 在同目录查找 math.c / math.h
  4. 读取 //@cgoal 注释行
  5. 解析出: add → math_Math_add, sub → math_Math_sub
  6. 替换 app.cgoal 中的符号引用
  7. 输出 app.c + app.h（带 @cgoal 元数据）
```

---

## 4. Goal 扩展语法

Goal 范式提供声明式数据流编排，通过管道（`|>`）串联步骤，编译期展开为顺序 C 函数调用。

### 4.1 步骤（step）

步骤是 Goal 的执行单元，本质上是 C 函数。定义采用标准 C 函数语法。

**语法形式**：
```cgoal
step 返回类型 步骤名(参数列表) {
    // C 代码，可使用所有扩展特性
}
```

**示例**：
```cgoal
step char* read_file(const char* path) {
    FILE* fp = fopen(path, "r");
    if (!fp) return NULL;
    char* buf = malloc(1024);
    fread(buf, 1, 1024, fp);
    fclose(fp);
    return buf;
}
```

步骤内部可以使用 `let`、`class` 等扩展特性，与普通函数一致。

---

### 4.2 目标（goal）

目标声明一个计算流程，内部使用管道编排步骤。

**语法形式**：
```cgoal
goal 返回类型 目标名(参数列表) {
    // 步骤管道或普通 C 语句
}
```

**示例**：
```cgoal
goal int analyze(const char* path) {
    read_file(path)
    |> count_lines()
    |> @lines
    printf("lines: %d\n", @lines);
    return @lines;
}
```

若声明了非 `void` 返回类型，必须在所有执行路径末尾显式 `return`。

---

### 4.3 目标实现（impl）

一个 `goal` 可以只声明签名（以分号结尾），然后通过多个 `impl` 提供具体实现。

**语法形式**：
```cgoal
goal int analyze(const char* path);

impl analyze using fast {
    // ...
}

impl analyze using safe {
    // ...
}
```

调用时可选择实现策略：
```cgoal
int n = analyze("data.txt") using fast;   // 指定实现
int m = analyze("data.txt");              // 使用默认（第一个 impl）
```

---

### 4.4 管道（`|>`）与数据流

管道将前一步的输出作为后一步的输入。编译期展开为顺序调用，**零运行时开销**。

**规则**：
- 管道值默认传递给下一个步骤的**第一个参数**。
- 若步骤有多个参数，其余参数需通过 `@` 命名数据或字面量显式提供。
- 推荐使用 `@` 捕获中间结果后进行显式调用。

**示例**：
```cgoal
goal int compute(int x) {
    step int get_value() { return x; }

    get_value() |> @val
    int r1 = add(@val, 10);
    int r2 = multiply(r1, 2);
    return r2;
}
```

---

### 4.5 命名中间数据（`@`）

使用 `@变量名` 捕获中间结果，作用域为整个 `goal` 体。

```cgoal
goal int process(const char* path) {
    read_file(path) |> @content
    count_lines(@content) |> @lines
    printf("lines: %d\n", @lines);
    return @lines;
}
```

---

### 4.6 管道内条件分支

管道支持 `if-else` 分支，用于根据中间结果分流。

```cgoal
goal const char* process(const char* path) {
    read_file(path) |> @content
    if (@content) {
        printf("file loaded\n");
        return @content;
    } else {
        return "(empty)";
    }
}
```

分支位于管道末尾时，各分支最后表达式的值即该分支返回值，类型必须兼容。

---

### 4.7 并行执行

- `A || B |> C`：A 与 B 并行执行，全部完成后，结果组成**匿名结构体**传给 C。
- `A | B |> C`：A 与 B 并行执行，任一完成即将其结果传给 C（竞态）。

`||` 生成的匿名结构体字段名为 `_0, _1, ...`，按书写顺序排列。

**示例**：
```cgoal
step const char* fetch_name() { return "test"; }
step int fetch_size() { return 1024; }

goal void run() {
    fetch_name() || fetch_size() |> @both
    printf("%s: %d\n", @both._0, @both._1);
}
```

若编译器未启用并行支持，则降级为顺序执行。

---

### 4.8 错误处理关键字

Goal 提供三个专用关键字，仅在 `step` 或 `goal` 体内有效。

| 关键字 | 作用 | 示例 |
|:---|:---|:---|
| `abort(msg)` | 终止整个 `goal` 的执行 | `abort("invalid input");` |
| `finish(val)` | 提前从当前 `step` 返回一个值（与 `return` 等价） | `finish(NULL);` |
| `skip` | 返回当前步骤类型的零值（`{0}` 或 `NULL`） | `skip;` |

`skip` 展开为 `return 0;` 或 `return NULL;` 或零初始化结构体，取决于返回类型。

---

### 4.9 编译期策略切换（`if constexpr`）

在 `goal` 体内可根据编译期常量选择不同实现。

```cgoal
const int USE_FAST = 1;

goal int process(const char* path) {
    if constexpr (USE_FAST) {
        return analyze(path) using fast;
    } else {
        return analyze(path) using safe;
    }
}
```

条件必须是整数常量表达式。

---

### 4.10 别名（alias）

为步骤或目标提供可读名称，用于调试输出或错误信息。

```cgoal
alias read_file = "读取文件";
alias count_lines = "计算行数";
```

---

## 5. 内存管理约定

- `class` 对象默认使用 **Boehm GC**（或等效垃圾回收器）分配。
- 转译后的 C 程序需链接 GC 库（如 `-lgc`）。
- 值类型（基本类型、普通 `struct`）不受 GC 管理，按 C 原有规则。
- 用户可以通过编译器选项切换为 `malloc` 分配（需手动 `free`），以兼容无 GC 环境。

---

## 6. 头文件（`.hgoal`）

### 6.1 声明与实现分离

CGoal 头文件遵循标准 C 的声明/实现分离模式：

```cgoal
// math.hgoal
namespace Math {
    int add(int a, int b);
    int sub(int a, int b);
}

double PI;
```

转换后 `math.h`：

```c
//@cgoal module: math
//@cgoal namespace: Math
//@cgoal   add  ->  math_Math_add
//@cgoal   sub  ->  math_Math_sub
//@cgoal namespace: (global)
//@cgoal   PI   ->  math_PI

#ifndef MATH_H
#define MATH_H

int math_Math_add(int a, int b);
int math_Math_sub(int a, int b);
extern double math_PI;

#endif
```

### 6.2 实现文件

```cgoal
// math.cgoal
#include "math.hgoal"

namespace Math {
    int add(int a, int b) {
        return a + b;
    }

    int sub(int a, int b) {
        return a - b;
    }
}

double PI = 3.14159;
```

---

## 7. 命令行工具

### 7.1 用法

```bash
cgoal <source.cgoal> [options]
```

### 7.2 选项

| 选项 | 说明 |
|------|------|
| `-o <dir>` | 指定输出目录（默认：源文件同目录） |
| `--no-cache` | 不读取已有 `.c`/`.h` 的元数据（单文件独立模式） |
| `--clean` | 删除所有生成文件后重新转换 |
| `--debug-ast` | 打印 AST 调试信息 |

### 7.3 示例

```bash
# 转换单个文件
cgoal math.cgoal

# 批量转换
cgoal *.cgoal

# 指定输出目录
cgoal math.cgoal -o build/

# 完整构建流程
cgoal math.cgoal         # 生成 math.c, math.h
cgoal app.cgoal          # 读取 math.h 元数据，生成 app.c, app.h
```

---

## 8. 语法快速参考

### 8.1 新增关键字

| 关键字 | 用法 |
|--------|------|
| `let` | 变量声明（类型推断） |
| `class` | 类定义 |
| `string` | 字符串类型（映射为 `char*`） |
| `namespace` | 定义命名空间块 |
| `using` | 导入命名空间或特定符号 |
| `extern` | 与 `"C"` 配合指定 C 链接规范 |
| `step` | Goal 执行单元 |
| `goal` | 目标定义（管道编排） |
| `impl` | 目标的多策略实现 |
| `alias` | 为步骤/目标指定可读名称 |
| `abort` | 终止整个 goal 执行 |
| `finish` | 提前从 step 返回 |
| `skip` | 返回当前步骤类型的零值 |
| `if constexpr` | 编译期条件分支 |

### 8.2 新增运算符

| 运算符 | 用法 |
|--------|------|
| `::` | 作用域解析：`namespace::symbol` |
| `\|>` | 管道：将前一步输出传入下一步 |
| `@` | 命名中间数据：`@变量名` |
| `\|\|` | 并行全完成：`A() \|\| B() \|> C()` |
| `\|` | 并行任一完成：`A() \| B() \|> C()` |

### 8.3 语法规则

```
external-declaration ::= ...
                       | namespace-definition
                       | using-directive
                       | using-declaration
                       | class-definition
                       | step-definition
                       | goal-definition
                       | impl-definition
                       | alias-definition
                       | extern-C-block

namespace-definition ::= NAMESPACE ID '{' external-declaration* '}'

using-directive      ::= USING NAMESPACE ID ';'

using-declaration    ::= USING ID '::' ID ';'

class-definition     ::= CLASS ID '{' field-declaration* '}'

let-declaration      ::= LET ID [':' type] '=' expression ';'

step-definition      ::= STEP type ID '(' param-list ')' compound-statement

goal-definition      ::= GOAL type ID '(' param-list ')' compound-statement
                      | GOAL type ID '(' param-list ')' ';'

impl-definition      ::= IMPL ID USING ID compound-statement

alias-definition     ::= ALIAS ID '=' STRING ';'

extern-C-block       ::= EXTERN STRING compound-statement
```

### 8.4 关键字冲突处理

`let`、`class`、`namespace`、`using`、`step`、`goal`、`impl`、`alias`、`abort`、`finish`、`skip` 不是 C 标准保留字。在 CGoal 中，它们是**上下文关键字**——仅在文件顶层和特定声明位置作为声明关键字，在表达式和语句中仍可作为普通标识符使用。

---

## 9. 完整示例

### 9.1 `person.cgoal`

```cgoal
// person.cgoal — 用户模型

namespace App {
    class Person {
        string name;
        int age;
    }

    step Person create_person(const char* name, int age) {
        let p = Person(name, age);
        return p;
    }

    goal int run(const char* name) {
        create_person(name, 30) |> @person
        printf("name: %s, age: %d\n", @person.name, @person.age);
        return @person.age;
    }
}

extern "C" {
    #include <stdio.h>
}

int main() {
    return App::run("Alice");
}
```

### 9.2 转译后的 `person.c`

```c
//@cgoal module: person
//@cgoal namespace: App
//@cgoal   create_person  ->  person_App_create_person
//@cgoal   run            ->  person_App_run

#include <gc.h>
#include <stdio.h>

typedef struct {
    char* name;
    int age;
} Person;

Person* person_App_create_person(const char* name, int age) {
    Person* p = (Person*)GC_malloc(sizeof(Person));
    p->name = (char*)name;
    p->age = age;
    return p;
}

int person_App_run(const char* name) {
    Person* _g0 = person_App_create_person(name, 30);
    printf("name: %s, age: %d\n", _g0->name, _g0->age);
    return _g0->age;
}

int main() {
    return person_App_run("Alice");
}
```

### 9.3 构建与运行

```bash
$ cgoal person.cgoal        # 生成 person.c + person.h
$ gcc person.c -lgc -o app  # 标准 C 编译链接
$ ./app
name: Alice, age: 30
```

---

## 10. 工具链流程（概念）

```
用户代码 (.cgoal / .hgoal)
    → 解析器（支持所有扩展语法）
    → AST
    → 语义分析（类型检查、作用域、名称修饰、GC 标记）
    → 转译器（生成标准 C 代码）
    → GCC/Clang + GC 库
    → 可执行文件
```

---

## 11. 附录：命名修饰速查

| 源文件 | 上下文 | 声明 | 修饰后 |
|--------|--------|------|--------|
| `math.cgoal` | 顶层 | `int add(...)` | `math_add` |
| `math.cgoal` | `namespace X` | `int foo()` | `math_X_foo` |
| `math.cgoal` | `namespace A::B` | `int bar()` | `math_A_B_bar` |
| `math.cgoal` | 顶层 `static` | `int helper()` | `helper`（不加前缀） |
| `app.cgoal` | 顶层 | `int main()` | `main`（保留原名） |
| `person.cgoal` | `namespace App` | `class Person` | `Person`（结构体标签不修饰） |
| `person.cgoal` | `namespace App` | `step create_person` | `person_App_create_person` |
| `person.cgoal` | `namespace App` | `goal run` | `person_App_run` |

---

*— CGoal 语言手册 1.0 —*

---

# CGoal Language Manual (English)

[English](#cgoal-language-manual-english) | [中文](#cgoal-语言手册)

> **Version**: 1.0  
---

## 1. Overview

CGoal is a superset of the C language, adding **modern syntax**, **namespaces and modularity**, and **declarative data flow orchestration (Goal paradigm)** on top of standard C. CGoal source files are compiled to standard C files (`.c` / `.h`) with the same name via the `cgoal` transpiler.

### Design Goals

- **C Superset**: All valid C code (C89/C99) is valid CGoal code.
- **Modern Syntax**: Provides more concise variable declarations, class definitions, and automatic memory management(not yet implemented).
- **Automatic Memory Management**: Objects of `class` types are managed by garbage collection by default, users don't need to manually free them.
- **Reference Semantics**: `class` objects are passed by reference by default, assignment shares the object.
- **Goal Paradigm**: Declarative data flow orchestration, connecting steps via pipes (`|>`), expanded at compile time with zero runtime overhead.
- **Standard C Output**: No additional runtime required, can be compiled and linked directly with GCC/Clang.

### File Extensions

| Type | Extension |
|------|-----------|
| CGoal source file | `.cgoal` |
| CGoal header file | `.hgoal` |
| Output C file | `.c` |
| Output header file | `.h` |

---

## 2. Basic Extended Syntax

### 2.1 Variable Declaration: `let`

**Syntax**:
```cgoal
let name: type = initializer;   // Explicit type
let name = initializer;         // Type inference (optional)
```

**Semantics**:
- Declares a variable with scope from the declaration point to the end of the current block.
- **Variables declared with `let` are pointers by default**, especially when the type is a `class`, the variable is a pointer to an object on the heap, managed by GC.
- For C basic types (`int`, `float`, `char`, etc.) or plain `struct`, `let` variables are still **value types** (stack-allocated) to maintain full compatibility with C.
- If the initializer is a constructor call (like `Person(...)`), the compiler automatically infers it as a pointer type.

**Translation Target (C Code)**:
- Reference type (`class`): Generate pointer declaration + heap allocation.
- Value type: Generate normal C declaration.

**Examples**:
```cgoal
let x: int = 5;               // Value type → int x = 5;
let name: string = "Alice";   // string maps to char* → char* name = "Alice";
let p = Person("Alice", 25);  // Reference type → Person* p = ...
```

---

### 2.2 Class Definition: `class`

**Syntax**:
```cgoal
class Person {
    string name;
    int age;
}
```

**Field Declaration Syntax**:
```
type field_name;
```

Field declarations are **completely consistent** with C struct fields: type first, field name second. Fields can be any valid C type (basic types, pointers, structs, `string`, etc.).

**Semantics**:
- Defines a class type, corresponding to a C struct underneath.
- All variables of this class are references (pointers), assignment shares the object.
- Supports `ClassName(arg1, arg2, ...)` syntax to create objects.
- Fields are arranged in declaration order.

**Translation Target (C Code)**:
```c
typedef struct {
    char* name;
    int age;
} Person;
```

**Rules**:
- `string` type maps to `char*`.
- Field syntax is exactly the same as C structs, no new field declaration order is introduced.

---

### 2.3 Constructor Call

**Syntax**:
```cgoal
let p = Person("Alice", 25);
```

**Semantics**:
- Creates a new object of this class (heap-allocated), initializes fields in parameter order.
- Number of parameters must match the number of fields.

**Translation Target (C Code)**:
```c
Person* p = (Person*)GC_malloc(sizeof(Person));
p->name = "Alice";
p->age = 25;
```

---

### 2.4 Member Access

**Syntax**:
```cgoal
p.age = 26;
printf("%d\n", p.age);
```

**Semantics**:
- Regardless of whether the variable is a value or reference, use `.` uniformly to access members.
- The compiler automatically decides whether to use `.` or `->` underneath.

**Translation Rules**:
- Value type → `variable.member`
- Reference type (pointer) → `variable->member`

---

### 2.5 Built-in Types

- **`string`**: Maps to `char*`.

(No built-in output functions, all output is done through standard C `printf`, user specifies format specifiers.)

---

## 3. Namespaces and Linkage Specification

### 3.1 Namespace Definition

**Syntax**:
```cgoal
namespace identifier {
    // Variable, function, type, struct definitions...
}
```

**Semantics**:
- Defines a namespace to avoid global symbol conflicts and provide semantic grouping.
- Supports nested namespaces.
- Use `::` to access namespace members.

**Example**:
```cgoal
namespace MyLib {
    int version = 1;
    void hello() { ... }
}

int main() {
    MyLib::hello();
    int v = MyLib::version;
    return 0;
}
```

**Translation Target (C Code)**:
- Symbols in the namespace are name-mangled, for example `MyLib::hello` becomes `MyLib_hello`.
- Mangling rule: `namespace_name_symbol_name`, nested with `_` connection.

---

### 3.2 File-Level Automatic Namespace Wrapping

**Rule**: When loading the main source file, the compiler automatically wraps its content in `namespace <filename> { ... }`.

**Effect**:
- All global symbols in the file automatically belong to the namespace named after the filename.
- Avoids symbol conflicts between multiple source files.
- User-defined namespaces are nested within the automatic namespace.

**Example**:
User source code `main.cgoal`:
```cgoal
int global_var = 100;
void foo() { ... }
```
Compiler actually processes:
```cgoal
namespace main {
    int global_var = 100;
    void foo() { ... }
}
```

---

### 3.3 Name Mangling Rules Summary

```
Full mangled name = filename + "_" + [namespace + "_"]* + APIname

Examples:
  math.cgoal, namespace Math, add()   → math_Math_add
  math.cgoal, namespace A::B, foo()   → math_A_B_foo
  math.cgoal, top-level, init()       → math_init
  app.cgoal, top-level, main()        → main
```

### 3.4 Cases Without Prefix

| Case | Description |
|------|-------------|
| `static` functions/variables | Already restricted to translation unit, no prefix needed |
| `main()` function | C runtime entry, must preserve original name |
| Symbols from `#include` | Standard C symbols from external headers |
| Local variables | Scope within function, no conflict risk |

---

### 3.5 `extern "C"` Linkage Specification

**Syntax**:
```cgoal
extern "C" {
    // Function declarations or definitions
}
// Or single declaration
extern "C" void printf(const char* format, ...);
```

**Semantics**:
- All functions and global variables declared in the `extern "C"` block have name mangling disabled.
- Generated symbol names are consistent with pure C compilation results.
- Used for interoperability with standard C libraries and OS APIs.

**Example**:
```cgoal
extern "C" {
    #include <stdio.h>
}
```

---

### 3.6 `using` Directive and Declaration

#### `using` Directive

```cgoal
using namespace <name>;
```

Imports **all symbols** from namespace `<name>` into the current scope.

- Can appear in any C scope (function body, namespace body, file top-level)
- During translation, imported symbols are replaced with their fully qualified names

**Example**:
```cgoal
// app.cgoal
using namespace Math;

int main() {
    int r = add(1, 2);    // → math_Math_add(1, 2)
    int s = sub(5, 3);    // → math_Math_sub(5, 3)
    return 0;
}
```

#### `using` Declaration

```cgoal
using <namespace>::<symbol>;
```

Imports only the specified symbol, not the entire namespace.

```cgoal
using Math::add;   // Only import add

int main() {
    int r = add(1, 2);    // → math_Math_add(1, 2)
    // sub(5, 3);         // Error: sub not imported
    return 0;
}
```

#### Name Conflict Handling

If two `using` directives introduce symbols with the same name, compilation fails (ambiguity):

```cgoal
using namespace Math;    // Exports add
using namespace Utils;   // Also exports add
// add(1, 2);            // Ambiguity! Compilation error
```

In this case, must use explicit declaration to disambiguate:

```cgoal
using Math::add;         // Explicitly specify
```

#### Nested `using` Does Not Propagate

```cgoal
// A.cgoal
namespace A {
    using namespace B;   // Only visible within A
    int x = B_foo;       // Correct
}

// app.cgoal
using namespace A;
// B_foo;                // Error: B's symbols don't propagate
```

#### Differences from C++

| Feature | C++ | CGoal |
|---------|-----|-------|
| `using namespace` in headers | Anti-pattern | Safe (file-level namespace isolation) |
| `using` imports types | Supports `class`/`enum` | Only variables and functions |
| `using` type alias | `using Foo = int;` | Not supported |
| Conflict resolution | More specialized wins | Direct error, requires explicit disambiguation |

---

### 3.7 Cross-File Symbol Resolution

#### Basic Principle

CGoal transpiler reads existing `.c` / `.h` files in the same directory and extracts `//@cgoal` metadata lines to resolve external symbols for `using` directives.

#### Metadata Comment Format

Each output `.c` and `.h` file header contains metadata:

```c
//@cgoal module: math
//@cgoal namespace: Math
//@cgoal   add  ->  math_Math_add
//@cgoal   sub  ->  math_Math_sub
//@cgoal namespace: (global)
//@cgoal   init  ->  math_init
```

#### Transpiler Resolution Process

```
cgoal app.cgoal

  1. Parse app.cgoal
  2. Discover "using namespace Math;"
  3. Find math.c / math.h in same directory
  4. Read //@cgoal comment lines
  5. Parse out: add → math_Math_add, sub → math_Math_sub
  6. Replace symbol references in app.cgoal
  7. Output app.c + app.h (with @cgoal metadata)
```

---

## 4. Goal Extended Syntax

The Goal paradigm provides declarative data flow orchestration, connecting steps via pipes (`|>`), expanded at compile time into sequential C function calls.

### 4.1 Step

A step is the execution unit of Goal, essentially a C function. Definition uses standard C function syntax.

**Syntax**:
```cgoal
step return_type step_name(parameter_list) {
    // C code, can use all extended features
}
```

**Example**:
```cgoal
step char* read_file(const char* path) {
    FILE* fp = fopen(path, "r");
    if (!fp) return NULL;
    char* buf = malloc(1024);
    fread(buf, 1, 1024, fp);
    fclose(fp);
    return buf;
}
```

Inside a step, you can use extended features like `let`, `class`, etc., just like regular functions.

---

### 4.2 Goal

A goal declares a computation flow, internally using pipes to orchestrate steps.

**Syntax**:
```cgoal
goal return_type goal_name(parameter_list) {
    // Step pipes or regular C statements
}
```

**Example**:
```cgoal
goal int analyze(const char* path) {
    read_file(path)
    |> count_lines()
    |> @lines
    printf("lines: %d\n", @lines);
    return @lines;
}
```

If a non-`void` return type is declared, must explicitly `return` at the end of all execution paths.

---

### 4.3 Goal Implementation (impl)

A `goal` can declare only the signature (ending with semicolon), then provide specific implementations through multiple `impl`.

**Syntax**:
```cgoal
goal int analyze(const char* path);

impl analyze using fast {
    // ...
}

impl analyze using safe {
    // ...
}
```

When calling, you can choose the implementation strategy:
```cgoal
int n = analyze("data.txt") using fast;   // Specify implementation
int m = analyze("data.txt");              // Use default (first impl)
```

---

### 4.4 Pipe (`|>`) and Data Flow

Pipes pass the output of the previous step as input to the next step. Compile-time expansion into sequential calls, **zero runtime overhead**.

**Rules**:
- Pipe value is passed to the **first parameter** of the next step by default.
- If a step has multiple parameters, the remaining parameters must be explicitly provided via `@` named data or literals.
- Recommended to use `@` to capture intermediate results and then make explicit calls.

**Example**:
```cgoal
goal int compute(int x) {
    step int get_value() { return x; }

    get_value() |> @val
    int r1 = add(@val, 10);
    int r2 = multiply(r1, 2);
    return r2;
}
```

---

### 4.5 Named Intermediate Data (`@`)

Use `@variable_name` to capture intermediate results, scope is the entire `goal` body.

```cgoal
goal int process(const char* path) {
    read_file(path) |> @content
    count_lines(@content) |> @lines
    printf("lines: %d\n", @lines);
    return @lines;
}
```

---

### 4.6 Conditional Branching in Pipes

Pipes support `if-else` branches for branching based on intermediate results.

```cgoal
goal const char* process(const char* path) {
    read_file(path) |> @content
    if (@content) {
        printf("file loaded\n");
        return @content;
    } else {
        return "(empty)";
    }
}
```

When a branch is at the end of a pipe, the value of the last expression in each branch is that branch's return value, types must be compatible.

---

### 4.7 Parallel Execution

- `A || B |> C`: A and B execute in parallel, after both complete, results form an **anonymous struct** passed to C.
- `A | B |> C`: A and B execute in parallel, whichever completes first passes its result to C (race condition).

`||` generates anonymous struct field names `_0, _1, ...`, in writing order.

**Example**:
```cgoal
step const char* fetch_name() { return "test"; }
step int fetch_size() { return 1024; }

goal void run() {
    fetch_name() || fetch_size() |> @both
    printf("%s: %d\n", @both._0, @both._1);
}
```

If compiler doesn't have parallel support enabled, it degrades to sequential execution.

---

### 4.8 Error Handling Keywords

Goal provides three special keywords, only valid in `step` or `goal` body.

| Keyword | Purpose | Example |
|:---|:---|:---|
| `abort(msg)` | Terminate entire `goal` execution | `abort("invalid input");` |
| `finish(val)` | Early return from current `step` (equivalent to `return`) | `finish(NULL);` |
| `skip` | Return zero value of current step type (`{0}` or `NULL`) | `skip;` |

`skip` expands to `return 0;` or `return NULL;` or zero-initialized struct, depending on return type.

---

### 4.9 Compile-Time Strategy Switching (`if constexpr`)

In a `goal` body, can choose different implementations based on compile-time constants.

```cgoal
const int USE_FAST = 1;

goal int process(const char* path) {
    if constexpr (USE_FAST) {
        return analyze(path) using fast;
    } else {
        return analyze(path) using safe;
    }
}
```

Condition must be an integer constant expression.

---

### 4.10 Alias

Provides readable names for steps or goals, used for debug output or error messages.

```cgoal
alias read_file = "Read File";
alias count_lines = "Count Lines";
```

---

## 5. Memory Management Conventions

- `class` objects use **Boehm GC** (or equivalent garbage collector) allocation by default.
- Translated C programs need to link GC library (like `-lgc`).
- Value types (basic types, plain `struct`) are not managed by GC, follow original C rules.
- Users can switch to `malloc` allocation via compiler options (requires manual `free`), to be compatible with non-GC environments.

---

## 6. Header Files (`.hgoal`)

### 6.1 Declaration and Implementation Separation

CGoal header files follow the standard C declaration/implementation separation pattern:

```cgoal
// math.hgoal
namespace Math {
    int add(int a, int b);
    int sub(int a, int b);
}

double PI;
```

Translated to `math.h`:

```c
//@cgoal module: math
//@cgoal namespace: Math
//@cgoal   add  ->  math_Math_add
//@cgoal   sub  ->  math_Math_sub
//@cgoal namespace: (global)
//@cgoal   PI   ->  math_PI

#ifndef MATH_H
#define MATH_H

int math_Math_add(int a, int b);
int math_Math_sub(int a, int b);
extern double math_PI;

#endif
```

### 6.2 Implementation File

```cgoal
// math.cgoal
#include "math.hgoal"

namespace Math {
    int add(int a, int b) {
        return a + b;
    }

    int sub(int a, int b) {
        return a - b;
    }
}

double PI = 3.14159;
```

---

## 7. Command Line Tool

### 7.1 Usage

```bash
cgoal <source.cgoal> [options]
```

### 7.2 Options

| Option | Description |
|--------|-------------|
| `-o <dir>` | Specify output directory (default: same directory as source file) |
| `--no-cache` | Don't read metadata from existing `.c`/`.h` (single file standalone mode) |
| `--clean` | Delete all generated files then re-translate |
| `--debug-ast` | Print AST debug information |

### 7.3 Examples

```bash
# Translate single file
cgoal math.cgoal

# Batch translate
cgoal *.cgoal

# Specify output directory
cgoal math.cgoal -o build/

# Complete build process
cgoal math.cgoal         # Generate math.c, math.h
cgoal app.cgoal          # Read math.h metadata, generate app.c, app.h
```

---

## 8. Syntax Quick Reference

### 8.1 New Keywords

| Keyword | Usage |
|---------|-------|
| `let` | Variable declaration (type inference) |
| `class` | Class definition |
| `string` | String type (maps to `char*`) |
| `namespace` | Define namespace block |
| `using` | Import namespace or specific symbol |
| `extern` | Specify C linkage with `"C"` |
| `step` | Goal execution unit |
| `goal` | Goal definition (pipe orchestration) |
| `impl` | Multiple strategy implementation for goal |
| `alias` | Specify readable name for step/goal |
| `abort` | Terminate entire goal execution |
| `finish` | Early return from step |
| `skip` | Return zero value of current step type |
| `if constexpr` | Compile-time conditional branch |

### 8.2 New Operators

| Operator | Usage |
|----------|-------|
| `::` | Scope resolution: `namespace::symbol` |
| `\|>` | Pipe: pass previous step output to next step |
| `@` | Named intermediate data: `@variable_name` |
| `\|\|` | Parallel all complete: `A() \|\| B() \|> C()` |
| `\|` | Parallel any complete: `A() \| B() \|> C()` |

### 8.3 Syntax Rules

```
external-declaration ::= ...
                       | namespace-definition
                       | using-directive
                       | using-declaration
                       | class-definition
                       | step-definition
                       | goal-definition
                       | impl-definition
                       | alias-definition
                       | extern-C-block

namespace-definition ::= NAMESPACE ID '{' external-declaration* '}'

using-directive      ::= USING NAMESPACE ID ';'

using-declaration    ::= USING ID '::' ID ';'

class-definition     ::= CLASS ID '{' field-declaration* '}'

let-declaration      ::= LET ID [':' type] '=' expression ';'

step-definition      ::= STEP type ID '(' param-list ')' compound-statement

goal-definition      ::= GOAL type ID '(' param-list ')' compound-statement
                      | GOAL type ID '(' param-list ')' ';'

impl-definition      ::= IMPL ID USING ID compound-statement

alias-definition     ::= ALIAS ID '=' STRING ';'

extern-C-block       ::= EXTERN STRING compound-statement
```

### 8.4 Keyword Conflict Handling

`let`, `class`, `namespace`, `using`, `step`, `goal`, `impl`, `alias`, `abort`, `finish`, `skip` are not C standard reserved words. In CGoal, they are **contextual keywords**—they only act as declaration keywords at file top-level and specific declaration positions, and can still be used as regular identifiers in expressions and statements.

---

## 9. Complete Example

### 9.1 `person.cgoal`

```cgoal
// person.cgoal — User model

namespace App {
    class Person {
        string name;
        int age;
    }

    step Person create_person(const char* name, int age) {
        let p = Person(name, age);
        return p;
    }

    goal int run(const char* name) {
        create_person(name, 30) |> @person
        printf("name: %s, age: %d\n", @person.name, @person.age);
        return @person.age;
    }
}

extern "C" {
    #include <stdio.h>
}

int main() {
    return App::run("Alice");
}
```

### 9.2 Translated `person.c`

```c
//@cgoal module: person
//@cgoal namespace: App
//@cgoal   create_person  ->  person_App_create_person
//@cgoal   run            ->  person_App_run

#include <gc.h>
#include <stdio.h>

typedef struct {
    char* name;
    int age;
} Person;

Person* person_App_create_person(const char* name, int age) {
    Person* p = (Person*)GC_malloc(sizeof(Person));
    p->name = (char*)name;
    p->age = age;
    return p;
}

int person_App_run(const char* name) {
    Person* _g0 = person_App_create_person(name, 30);
    printf("name: %s, age: %d\n", _g0->name, _g0->age);
    return _g0->age;
}

int main() {
    return person_App_run("Alice");
}
```

### 9.3 Build and Run

```bash
$ cgoal person.cgoal        # Generate person.c + person.h
$ gcc person.c -lgc -o app  # Standard C compile and link
$ ./app
name: Alice, age: 30
```

---

## 10. Toolchain Process (Conceptual)

```
User code (.cgoal / .hgoal)
    → Parser (supports all extended syntax)
    → AST
    → Semantic analysis (type checking, scope, name mangling, GC marking)
    → Transpiler (generate standard C code)
    → GCC/Clang + GC library
    → Executable
```

---

## 11. Appendix: Name Mangling Quick Reference

| Source File | Context | Declaration | Mangled |
|-------------|---------|-------------|---------|
| `math.cgoal` | Top-level | `int add(...)` | `math_add` |
| `math.cgoal` | `namespace X` | `int foo()` | `math_X_foo` |
| `math.cgoal` | `namespace A::B` | `int bar()` | `math_A_B_bar` |
| `math.cgoal` | Top-level `static` | `int helper()` | `helper` (no prefix) |
| `app.cgoal` | Top-level | `int main()` | `main` (preserve original name) |
| `person.cgoal` | `namespace App` | `class Person` | `Person` (struct tag not mangled) |
| `person.cgoal` | `namespace App` | `step create_person` | `person_App_create_person` |
| `person.cgoal` | `namespace App` | `goal run` | `person_App_run` |

---

*— CGoal Language Manual 1.0 —*