# 回执上下文策略逐题结果与失败证据

全部 36 条轨迹中，29 条冷验收通过，7 条失败。评分状态、执行停止原因与具体日志分别保存。

## 6 题逐组通过数

| 任务 | baseline | early | early_state |
| --- | ---: | ---: | ---: |
| `fmtlib__fmt-2070` | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3537` | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3713` | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3750` | 2/2 | 1/2 | 2/2 |
| `fmtlib__fmt-3819` | 0/2 | 0/2 | 0/2 |
| `fmtlib__fmt-493` | 2/2 | 2/2 | 2/2 |

## 逐条失败与原始轨迹

日志链接保存冷构建、测试输出与候选补丁全文。原始轨迹包含完整模型请求、工具回执、SQLite 事件及源码身份。

### trial-035 · fmtlib__fmt-3750 · early · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570821484)。

F2P：0/1 通过；其余状态：`format-test`=not_run。
P2P：0/19 通过；其余状态：`args-test`=not_run, `assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-fp-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `enforce-checks-test`=not_run, `format-impl-test`=not_run, `gtest-extra-test`=not_run, `os-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run, `std-test`=not_run, `unicode-test`=not_run, `xchar-test`=not_run。

[候选补丁](evidence/trial-035/candidate.patch)。

[native-oracle-build.log](evidence/trial-035/native-oracle-build.log)

从第 11 行起：

```text
/src/include/fmt/format-inl.h:141:19:   required from here
/src/include/fmt/format.h:2181:45: error: ‘make_write_int_arg’ was not declared in this scope, and no declarations were found by argument-dependent lookup at the point of instantiation [-fpermissive]
 2181 |     return write_int(out, make_write_int_arg(value, specs.sign), specs,
      |                           ~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:2206:20: note: ‘template<class T> constexpr fmt::v10::detail::write_int_arg<typename std::conditional<((num_bits<T>() <= 32) && (!0)), unsigned int, typename std::conditional<(num_bits<T>() <= 64), long unsigned int, __int128 unsigned>::type>::type> fmt::v10::detail::make_write_int_arg(T, fmt::v10::sign_t)’ declared here, later in the translation unit
 2206 | FMT_CONSTEXPR auto make_write_int_arg(T value, sign_t sign)
      |                    ^~~~~~~~~~~~~~~~~~
/src/include/fmt/format.h: In instantiation of ‘OutputIt fmt::v10::detail::write_int(OutputIt, UInt, unsigned int, const fmt::v10::format_specs<Char>&, const digit_grouping<Char>&) [with OutputIt = fmt::v10::appender; UInt = __int128 unsigned; Char = char]’:
/src/include/fmt/format.h:2231:14:   required from ‘bool fmt::v10::detail::loc_writer<Char>::operator()(T) [with T = __int128; typename std::enable_if<std::integral_constant<bool, (((fmt::v10::detail::is_integral<T>::value && (! std::is_same<T, bool>::value)) && (! std::is_same<T, char>::value)) && (! std::is_same<T, wchar_t>::value))>::value, int>::type <anonymous> = 0; Char = char]’
/src/include/fmt/core.h:1697:15:   required from ‘constexpr decltype (vis(0)) fmt::v10::visit_format_arg(Visitor&&, const basic_format_arg<Context>&) [with Visitor = detail::loc_writer<>&; Context = basic_format_context<appender, char>; decltype (vis(0)) = bool]’
```

从第 22 行起：

```text
/src/include/fmt/format-inl.h:141:19:   required from here
/src/include/fmt/format.h:2181:45: error: ‘make_write_int_arg’ was not declared in this scope, and no declarations were found by argument-dependent lookup at the point of instantiation
 2181 |     return write_int(out, make_write_int_arg(value, specs.sign), specs,
      |                           ~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:2206:20: note: ‘template<class T> constexpr fmt::v10::detail::write_int_arg<typename std::conditional<((num_bits<T>() <= 32) && (!0)), unsigned int, typename std::conditional<(num_bits<T>() <= 64), long unsigned int, __int128 unsigned>::type>::type> fmt::v10::detail::make_write_int_arg(T, fmt::v10::sign_t)’ declared here, later in the translation unit
 2206 | FMT_CONSTEXPR auto make_write_int_arg(T value, sign_t sign)
      |                    ^~~~~~~~~~~~~~~~~~
[3/67] Building CXX object test/CMakeFiles/test-main.dir/test-main.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-035/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-035/native-oracle-inventory.log)

### trial-018 · fmtlib__fmt-3819 · baseline · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570013215)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-018/candidate.patch)。

[native-oracle-build.log](evidence/trial-018/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-018/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-018/native-oracle-ctest.log)

从第 29 行起：

```text
[ RUN      ] args_test.reserve
/src/test/args-test.cc:167: Failure
Expected equality of these values:
  "42 and 1.5"
  result
    Which is: "42 and cust=21954"
[  FAILED  ] args_test.reserve (0 ms)
[ RUN      ] args_test.throw_on_copy
[       OK ] args_test.throw_on_copy (0 ms)
[ RUN      ] args_test.move_constructor
```

从第 44 行起：

```text
[  PASSED  ] 13 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] args_test.reserve

 1 FAILED TEST

      Start  2: base-test
 2/20 Test  #2: base-test ........................   Passed    0.00 sec
      Start  3: assert-test
 3/20 Test  #3: assert-test ......................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-018/native-oracle-inventory.log)

### trial-032 · fmtlib__fmt-3819 · baseline · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570796418)。

F2P：0/1 通过；其余状态：`args-test`=not_run。
P2P：0/19 通过；其余状态：`assert-test`=not_run, `base-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-fp-test`=not_run, `compile-test`=not_run, `enforce-checks-test`=not_run, `format-impl-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `os-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run, `std-test`=not_run, `unicode-test`=not_run, `xchar-test`=not_run。

[候选补丁](evidence/trial-032/candidate.patch)。

[native-oracle-build.log](evidence/trial-032/native-oracle-build.log)

从第 9 行起：

```text
/src/src/format.cc:32:75:   required from here
/src/include/fmt/format.h:4272:21: error: ‘class fmt::v10::basic_format_parse_context<char>’ has no member named ‘advance_to_arg_id’
 4272 |       parse_context.advance_to_arg_id(arg_id);
      |       ~~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
[3/71] Building CXX object test/CMakeFiles/test-main.dir/test-main.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-032/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-032/native-oracle-inventory.log)

### trial-009 · fmtlib__fmt-3819 · early · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13569787965)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-009/candidate.patch)。

[native-oracle-build.log](evidence/trial-009/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-009/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-009/native-oracle-ctest.log)

从第 23 行起：

```text
[ RUN      ] args_test.named_with_manual_index
unknown file: Failure
C++ exception with description "cannot switch from manual to automatic argument indexing" thrown in the test body.
[  FAILED  ] args_test.named_with_manual_index (0 ms)
[ RUN      ] args_test.named_custom_format
[       OK ] args_test.named_custom_format (0 ms)
[ RUN      ] args_test.clear
[       OK ] args_test.clear (0 ms)
[ RUN      ] args_test.reserve
/src/test/args-test.cc:167: Failure
```

从第 36 行起：

```text
    Which is: "42 and 42"
[  FAILED  ] args_test.reserve (0 ms)
[ RUN      ] args_test.throw_on_copy
[       OK ] args_test.throw_on_copy (0 ms)
[ RUN      ] args_test.move_constructor
[       OK ] args_test.move_constructor (0 ms)
[----------] 14 tests from args_test (0 ms total)

[----------] Global test environment tear-down
[==========] 14 tests from 1 test suite ran. (0 ms total)
```

从第 46 行起：

```text
[  PASSED  ] 12 tests.
[  FAILED  ] 2 tests, listed below:
[  FAILED  ] args_test.named_with_manual_index
[  FAILED  ] args_test.reserve

 2 FAILED TESTS

      Start  2: base-test
 2/20 Test  #2: base-test ........................   Passed    0.00 sec
      Start  3: assert-test
```

[native-oracle-inventory.log](evidence/trial-009/native-oracle-inventory.log)

### trial-002 · fmtlib__fmt-3819 · early · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570135916)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-002/candidate.patch)。

[native-oracle-build.log](evidence/trial-002/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-002/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-002/native-oracle-ctest.log)

从第 21 行起：

```text
[ RUN      ] args_test.named_with_automatic_index
/src/test/args-test.cc:119: Failure
Expected equality of these values:
  "1 2 3 4"
  fmt::vformat("{} {a1} {a2} {}", store)
    Which is: "1 2 3 2"
[  FAILED  ] args_test.named_with_automatic_index (0 ms)
[ RUN      ] args_test.named_with_manual_index
[       OK ] args_test.named_with_manual_index (0 ms)
[ RUN      ] args_test.named_custom_format
```

从第 44 行起：

```text
[  PASSED  ] 13 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] args_test.named_with_automatic_index

 1 FAILED TEST

      Start  2: base-test
 2/20 Test  #2: base-test ........................   Passed    0.00 sec
      Start  3: assert-test
 3/20 Test  #3: assert-test ......................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-002/native-oracle-inventory.log)

### trial-006 · fmtlib__fmt-3819 · early_state · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570105911)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-006/candidate.patch)。

[native-oracle-build.log](evidence/trial-006/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-006/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-006/native-oracle-ctest.log)

从第 21 行起：

```text
[ RUN      ] args_test.named_with_automatic_index
/src/test/args-test.cc:119: Failure
Expected equality of these values:
  "1 2 3 4"
  fmt::vformat("{} {a1} {a2} {}", store)
    Which is: "1 2 3 2"
[  FAILED  ] args_test.named_with_automatic_index (0 ms)
[ RUN      ] args_test.named_with_manual_index
[       OK ] args_test.named_with_manual_index (0 ms)
[ RUN      ] args_test.named_custom_format
```

从第 44 行起：

```text
[  PASSED  ] 13 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] args_test.named_with_automatic_index

 1 FAILED TEST

      Start  2: base-test
 2/20 Test  #2: base-test ........................   Passed    0.00 sec
      Start  3: assert-test
 3/20 Test  #3: assert-test ......................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-006/native-oracle-inventory.log)

### trial-028 · fmtlib__fmt-3819 · early_state · r2

冷评分：`EMPTY_CANDIDATE`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42343832567/artifacts/13570830096)。

执行结束时未形成非空候选补丁，冷构建与测试保持未执行状态。
