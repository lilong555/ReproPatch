# 回执上下文策略逐题结果与失败证据

全部 190 条轨迹中，159 条冷验收通过，31 条失败。评分状态、执行停止原因与具体日志分别保存。

## 19 题逐组通过数

| 任务 | baseline | diagnostics | dedup | state | combined |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fmtlib__fmt-1361` | 1/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| `fmtlib__fmt-1390` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-2070` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2292` | 1/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2310` | 2/2 | 1/2 | 0/2 | 1/2 | 0/2 |
| `fmtlib__fmt-2317` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2610` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-2940` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3248` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3260` | 1/2 | 1/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3272` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3537` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3713` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3727` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3732` | 1/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| `fmtlib__fmt-3734` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3750` | 2/2 | 2/2 | 2/2 | 2/2 | 1/2 |
| `fmtlib__fmt-3819` | 0/2 | 0/2 | 0/2 | 2/2 | 0/2 |
| `fmtlib__fmt-493` | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

## 逐条失败与原始轨迹

日志链接保存冷构建、测试输出与候选补丁全文。原始轨迹包含完整模型请求、工具回执、SQLite 事件及源码身份。

### trial-046 · fmtlib__fmt-1361 · baseline · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13561741334)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-046/candidate.patch)。

[native-oracle-build.log](evidence/trial-046/native-oracle-build.log)

从第 32 行起：

```text
/src/include/fmt/format-inl.h:1347:23:   required from here
/src/include/fmt/format.h:210:30: error: static assertion failed: size mismatch
  210 |   static_assert(sizeof(Dest) == sizeof(Source), "size mismatch");
      |                 ~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:210:30: note: the comparison reduces to ‘(8 == 4)’
[3/51] Building CXX object test/CMakeFiles/gmock.dir/gmock-gtest-all.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-046/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-046/native-oracle-inventory.log)

### trial-042 · fmtlib__fmt-1361 · combined · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13561676217)。

F2P：1/2 通过；其余状态：`format-impl-test`=failed。
P2P：15/15 通过；其余状态：全部通过。

[候选补丁](evidence/trial-042/candidate.patch)。

[native-oracle-build.log](evidence/trial-042/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-042/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-042/native-oracle-ctest.log)

从第 54 行起：

```text
[ RUN      ] FPTest.ComputeFloatBoundaries
/src/test/format-impl-test.cc:247: Failure
Value of: lower.f
  Actual: 6755399172620288
Expected: vlower.f
Which is: 13835057505526349824
/src/test/format-impl-test.cc:248: Failure
Value of: lower.e
  Actual: -52
Expected: vlower.e
```

从第 64 行起：

```text
Which is: -63
/src/test/format-impl-test.cc:249: Failure
Value of: upper.f
  Actual: 6755399709491200
Expected: vupper.f
Which is: 13835058605037977600
/src/test/format-impl-test.cc:250: Failure
Value of: upper.e
  Actual: -52
Expected: vupper.e
```

从第 74 行起：

```text
Which is: -63
/src/test/format-impl-test.cc:247: Failure
Value of: lower.f
  Actual: 4503599493152768
Expected: vlower.f
Which is: 9223371761976868864
/src/test/format-impl-test.cc:248: Failure
Value of: lower.e
  Actual: -52
Expected: vlower.e
```

从第 84 行起：

```text
Which is: -63
/src/test/format-impl-test.cc:249: Failure
Value of: upper.f
  Actual: 4503599895805952
Expected: vupper.f
Which is: 9223372586610589696
/src/test/format-impl-test.cc:250: Failure
Value of: upper.e
  Actual: -52
Expected: vupper.e
```

[native-oracle-inventory.log](evidence/trial-042/native-oracle-inventory.log)

### trial-031 · fmtlib__fmt-1361 · combined · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560851838)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-031/candidate.patch)。

[native-oracle-build.log](evidence/trial-031/native-oracle-build.log)

从第 37 行起：

```text
/src/test/format-impl-test.cc:329:15:   required from here
/src/include/fmt/format.h:210:30: error: static assertion failed: size mismatch
  210 |   static_assert(sizeof(Dest) == sizeof(Source), "size mismatch");
      |                 ~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:210:30: note: the comparison reduces to ‘(8 == 4)’
[23/51] Building CXX object test/CMakeFiles/format-test.dir/format-test.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-031/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-031/native-oracle-inventory.log)

### trial-145 · fmtlib__fmt-1361 · dedup · r1

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13564254944)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-145/candidate.patch)。

[native-oracle-build.log](evidence/trial-145/native-oracle-build.log)

从第 39 行起：

```text
/src/test/format-impl-test.cc:329:15:   required from here
/src/include/fmt/format.h:210:30: error: static assertion failed: size mismatch
  210 |   static_assert(sizeof(Dest) == sizeof(Source), "size mismatch");
      |                 ~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:210:30: note: the comparison reduces to ‘(8 == 4)’
[23/51] Building CXX object test/CMakeFiles/format-test.dir/format-test.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-145/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-145/native-oracle-inventory.log)

### trial-158 · fmtlib__fmt-1361 · dedup · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565436505)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-158/candidate.patch)。

[native-oracle-build.log](evidence/trial-158/native-oracle-build.log)

从第 32 行起：

```text
/src/include/fmt/format-inl.h:1342:23:   required from here
/src/include/fmt/format.h:210:30: error: static assertion failed: size mismatch
  210 |   static_assert(sizeof(Dest) == sizeof(Source), "size mismatch");
      |                 ~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:210:30: note: the comparison reduces to ‘(8 == 4)’
[3/51] Building CXX object test/CMakeFiles/gmock.dir/gmock-gtest-all.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-158/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-158/native-oracle-inventory.log)

### trial-166 · fmtlib__fmt-1361 · diagnostics · r1

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565352299)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-166/candidate.patch)。

[native-oracle-build.log](evidence/trial-166/native-oracle-build.log)

从第 16 行起：

```text
/usr/bin/ld: test/CMakeFiles/color-test.dir/color-test.cc.o: in function `void fmt::v6::internal::basic_writer<fmt::v6::buffer_range<char> >::write_fp<float, true>(float, fmt::v6::basic_format_specs<char> const&)':
color-test.cc:(.text._ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIcEEE8write_fpIfLb1EEEvT_RKNS0_18basic_format_specsIcEE[_ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIcEEE8write_fpIfLb1EEEvT_RKNS0_18basic_format_specsIcEE]+0x122): undefined reference to `bool fmt::v6::internal::grisu_format<double, 0>(double, fmt::v6::internal::buffer<char>&, int, unsigned int, int&)'
/usr/bin/ld: test/CMakeFiles/color-test.dir/color-test.cc.o: in function `void fmt::v6::internal::basic_writer<fmt::v6::buffer_range<char> >::write_fp<double, true>(double, fmt::v6::basic_format_specs<char> const&)':
color-test.cc:(.text._ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIcEEE8write_fpIdLb1EEEvT_RKNS0_18basic_format_specsIcEE[_ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIcEEE8write_fpIdLb1EEEvT_RKNS0_18basic_format_specsIcEE]+0x131): undefined reference to `bool fmt::v6::internal::grisu_format<double, 0>(double, fmt::v6::internal::buffer<char>&, int, unsigned int, int&)'
/usr/bin/ld: libfmt.a(format.cc.o): in function `void fmt::v6::internal::basic_writer<fmt::v6::buffer_range<wchar_t> >::write_fp<float, true>(float, fmt::v6::basic_format_specs<wchar_t> const&)':
format.cc:(.text._ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIwEEE8write_fpIfLb1EEEvT_RKNS0_18basic_format_specsIwEE[_ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIwEEE8write_fpIfLb1EEEvT_RKNS0_18basic_format_specsIwEE]+0x123): undefined reference to `bool fmt::v6::internal::grisu_format<double, 0>(double, fmt::v6::internal::buffer<char>&, int, unsigned int, int&)'
/usr/bin/ld: libfmt.a(format.cc.o): in function `void fmt::v6::internal::basic_writer<fmt::v6::buffer_range<wchar_t> >::write_fp<double, true>(double, fmt::v6::basic_format_specs<wchar_t> const&)':
format.cc:(.text._ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIwEEE8write_fpIdLb1EEEvT_RKNS0_18basic_format_specsIwEE[_ZN3fmt2v68internal12basic_writerINS0_12buffer_rangeIwEEE8write_fpIdLb1EEEvT_RKNS0_18basic_format_specsIwEE]+0x13d): undefined reference to `bool fmt::v6::internal::grisu_format<double, 0>(double, fmt::v6::internal::buffer<char>&, int, unsigned int, int&)'
/usr/bin/ld: libfmt.a(format.cc.o):(.data.rel+0x0): undefined reference to `bool fmt::v6::internal::grisu_format<double, 0>(double, fmt::v6::internal::buffer<char>&, int, unsigned int, int&)'
collect2: error: ld returned 1 exit status
```

[native-oracle-configure.log](evidence/trial-166/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-166/native-oracle-inventory.log)

### trial-130 · fmtlib__fmt-1361 · state · r1

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13564267443)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-130/candidate.patch)。

[native-oracle-build.log](evidence/trial-130/native-oracle-build.log)

从第 18 行起：

```text
/src/src/format.cc:17:68:   required from here
/src/include/fmt/format.h:210:30: error: static assertion failed: size mismatch
  210 |   static_assert(sizeof(Dest) == sizeof(Source), "size mismatch");
      |                 ~~~~~~~~~~~~~^~~~~~~~~~~~~~~~~
/src/include/fmt/format.h:210:30: note: the comparison reduces to ‘(8 == 4)’
[3/51] Building CXX object test/CMakeFiles/gmock.dir/gmock-gtest-all.cc.o
ninja: build stopped: subcommand failed.
```

[native-oracle-configure.log](evidence/trial-130/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-130/native-oracle-inventory.log)

### trial-160 · fmtlib__fmt-1361 · state · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565571666)。

F2P：0/2 通过；其余状态：`format-impl-test`=not_run, `grisu-test`=not_run。
P2P：0/15 通过；其余状态：`assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `custom-formatter-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `locale-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `posix-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run。

[候选补丁](evidence/trial-160/candidate.patch)。

[native-oracle-build.log](evidence/trial-160/native-oracle-build.log)

从第 4 行起：

```text
/usr/bin/c++ -DFMT_LOCALE -I/src/include -O3 -DNDEBUG -std=gnu++11 -MD -MT CMakeFiles/fmt.dir/src/format.cc.o -MF CMakeFiles/fmt.dir/src/format.cc.o.d -o CMakeFiles/fmt.dir/src/format.cc.o -c /src/src/format.cc
/src/src/format.cc:15:52: error: no matches converting function ‘grisu_format’ to type ‘bool (*)(double, class fmt::v6::internal::buffer<char>&, int, unsigned int, int&)’
   15 |                                  int&) = internal::grisu_format;
      |                                                    ^~~~~~~~~~~~
In file included from /src/src/format.cc:8:
/src/include/fmt/format-inl.h:1036:6: note: candidates are: ‘template<class Double, typename std::enable_if<(sizeof (Double) == sizeof (long unsigned int)), int>::type <anonymous> > bool fmt::v6::internal::grisu_format(Double, buffer<char>&, int, unsigned int, int&)’
 1036 | bool grisu_format(Double value, buffer<char>& buf, int precision,
      |      ^~~~~~~~~~~~
In file included from /src/include/fmt/format-inl.h:11:
/src/include/fmt/format.h:1122:13: note:                 ‘template<class Double, typename std::enable_if<(sizeof (Double) != sizeof (long unsigned int)), int>::type <anonymous> > bool fmt::v6::internal::grisu_format(Double, buffer<char>&, int, unsigned int, int&, bool)’
```

[native-oracle-configure.log](evidence/trial-160/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-160/native-oracle-inventory.log)

### trial-030 · fmtlib__fmt-1390 · combined · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560203714)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-030/candidate.patch)。

[native-oracle-build.log](evidence/trial-030/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-030/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-030/native-oracle-ctest.log)

从第 294 行起：

```text
[ RUN      ] FormatTest.FormatUTF8Precision
/src/test/format-test.cc:2631: Failure
Value of: 5
Expected: result.size()
Which is: 4
/src/test/format-test.cc:2632: Failure
Value of: str.substr(0, 5)
  Actual: { 99, 97, 102, 195, 169 }
Expected: result
Which is: { 99, 97, 102, 195 }
```

从第 303 行起：

```text
Which is: { 99, 97, 102, 195 }
[  FAILED  ] FormatTest.FormatUTF8Precision (0 ms)
[----------] 29 tests from FormatTest (0 ms total)

[----------] 1 test from StrTest
[ RUN      ] StrTest.Convert
[       OK ] StrTest.Convert (0 ms)
[----------] 1 test from StrTest (0 ms total)

[----------] 2 tests from LiteralsTest
```

从第 321 行起：

```text
[  PASSED  ] 125 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] FormatTest.FormatUTF8Precision

 1 FAILED TEST

      Start  8: format-impl-test
 8/17 Test  #8: format-impl-test .................   Passed    0.00 sec
      Start  9: locale-test
 9/17 Test  #9: locale-test ......................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-030/native-oracle-inventory.log)

### trial-157 · fmtlib__fmt-2292 · baseline · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565432154)。

F2P：0/1 通过；其余状态：`chrono-test`=failed。
P2P：17/17 通过；其余状态：全部通过。

[候选补丁](evidence/trial-157/candidate.patch)。

[native-oracle-build.log](evidence/trial-157/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-157/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-157/native-oracle-ctest.log)

从第 23 行起：

```text
[ RUN      ] chrono_test.time_point
/src/test/chrono-test.cc:106: Failure
Expected equality of these values:
  "01.023"
  fmt::format("{:%S}", t3)
    Which is: "01023"
[  FAILED  ] chrono_test.time_point (0 ms)
[ RUN      ] chrono_test.format_default
[       OK ] chrono_test.format_default (0 ms)
[ RUN      ] chrono_test.format_wide
```

从第 69 行起：

```text
[  PASSED  ] 23 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] chrono_test.time_point

 1 FAILED TEST

      Start  4: color-test
 4/18 Test  #4: color-test .......................   Passed    0.00 sec
      Start  5: core-test
 5/18 Test  #5: core-test ........................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-157/native-oracle-inventory.log)

### trial-175 · fmtlib__fmt-2310 · combined · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565992121)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-175/candidate.patch)。

[native-oracle-build.log](evidence/trial-175/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-175/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-175/native-oracle-ctest.log)

从第 99 行起：

```text
[ RUN      ] format_test.width
/src/test/format-test.cc:748: Failure
Expected equality of these values:
  fmt::format("{:>06.0f}", 0.00884311)
    Which is: "     0"
  "000000"
[  FAILED  ] format_test.width (0 ms)
[ RUN      ] format_test.runtime_width
[       OK ] format_test.runtime_width (0 ms)
[ RUN      ] format_test.precision
```

从第 136 行起：

```text
[ RUN      ] format_test.format_nan
/src/test/format-test.cc:1275: Failure
Expected equality of these values:
  "  +nan"
  fmt::format("{:+06}", nan)
    Which is: "00+nan"
/src/test/format-test.cc:1281: Failure
Expected equality of these values:
  "  -nan"
  fmt::format("{:+06}", -nan)
```

从第 146 行起：

```text
    Which is: "00-nan"
[  FAILED  ] format_test.format_nan (0 ms)
[ RUN      ] format_test.format_infinity
/src/test/format-test.cc:1297: Failure
Expected equality of these values:
  "  +inf"
  fmt::format("{:+06}", inf)
    Which is: "00+inf"
/src/test/format-test.cc:1298: Failure
Expected equality of these values:
```

从第 158 行起：

```text
    Which is: "00-inf"
[  FAILED  ] format_test.format_infinity (0 ms)
[ RUN      ] format_test.format_long_double
[       OK ] format_test.format_long_double (0 ms)
[ RUN      ] format_test.format_char
[       OK ] format_test.format_char (0 ms)
[ RUN      ] format_test.format_volatile_char
[       OK ] format_test.format_volatile_char (0 ms)
[ RUN      ] format_test.format_unsigned_char
[       OK ] format_test.format_unsigned_char (0 ms)
```

[native-oracle-inventory.log](evidence/trial-175/native-oracle-inventory.log)

### trial-018 · fmtlib__fmt-2310 · combined · r2

冷评分：`EMPTY_CANDIDATE`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560516423)。

执行结束时未形成非空候选补丁，冷构建与测试保持未执行状态。

### trial-089 · fmtlib__fmt-2310 · dedup · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13562972092)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-089/candidate.patch)。

[native-oracle-build.log](evidence/trial-089/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-089/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-089/native-oracle-ctest.log)

从第 99 行起：

```text
[ RUN      ] format_test.width
/src/test/format-test.cc:748: Failure
Expected equality of these values:
  fmt::format("{:>06.0f}", 0.00884311)
    Which is: "     0"
  "000000"
[  FAILED  ] format_test.width (0 ms)
[ RUN      ] format_test.runtime_width
[       OK ] format_test.runtime_width (0 ms)
[ RUN      ] format_test.precision
```

从第 245 行起：

```text
[  PASSED  ] 103 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] format_test.width

 1 FAILED TEST

      Start  8: format-impl-test
 8/17 Test  #8: format-impl-test .................   Passed    0.01 sec
      Start  9: ostream-test
 9/17 Test  #9: ostream-test .....................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-089/native-oracle-inventory.log)

### trial-026 · fmtlib__fmt-2310 · dedup · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13561205078)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-026/candidate.patch)。

[native-oracle-build.log](evidence/trial-026/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-026/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-026/native-oracle-ctest.log)

从第 99 行起：

```text
[ RUN      ] format_test.width
/src/test/format-test.cc:748: Failure
Expected equality of these values:
  fmt::format("{:>06.0f}", 0.00884311)
    Which is: "     0"
  "000000"
[  FAILED  ] format_test.width (0 ms)
[ RUN      ] format_test.runtime_width
[       OK ] format_test.runtime_width (0 ms)
[ RUN      ] format_test.precision
```

从第 245 行起：

```text
[  PASSED  ] 103 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] format_test.width

 1 FAILED TEST

      Start  8: format-impl-test
 8/17 Test  #8: format-impl-test .................   Passed    0.01 sec
      Start  9: ostream-test
 9/17 Test  #9: ostream-test .....................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-026/native-oracle-inventory.log)

### trial-001 · fmtlib__fmt-2310 · diagnostics · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13559763316)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-001/candidate.patch)。

[native-oracle-build.log](evidence/trial-001/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-001/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-001/native-oracle-ctest.log)

从第 131 行起：

```text
[ RUN      ] format_test.format_nan
/src/test/format-test.cc:1276: Failure
Expected equality of these values:
  "+nan  "
  fmt::format("{:<+06}", nan)
    Which is: "  +nan"
/src/test/format-test.cc:1277: Failure
Expected equality of these values:
  " +nan "
  fmt::format("{:^+06}", nan)
```

从第 141 行起：

```text
    Which is: "  +nan"
[  FAILED  ] format_test.format_nan (0 ms)
[ RUN      ] format_test.format_infinity
/src/test/format-test.cc:1299: Failure
Expected equality of these values:
  "+inf  "
  fmt::format("{:<+06}", inf)
    Which is: "  +inf"
/src/test/format-test.cc:1300: Failure
Expected equality of these values:
```

从第 153 行起：

```text
    Which is: "  +inf"
[  FAILED  ] format_test.format_infinity (0 ms)
[ RUN      ] format_test.format_long_double
[       OK ] format_test.format_long_double (0 ms)
[ RUN      ] format_test.format_char
[       OK ] format_test.format_char (0 ms)
[ RUN      ] format_test.format_volatile_char
[       OK ] format_test.format_volatile_char (0 ms)
[ RUN      ] format_test.format_unsigned_char
[       OK ] format_test.format_unsigned_char (0 ms)
```

从第 260 行起：

```text
[  PASSED  ] 102 tests.
[  FAILED  ] 2 tests, listed below:
[  FAILED  ] format_test.format_nan
[  FAILED  ] format_test.format_infinity

 2 FAILED TESTS

      Start  8: format-impl-test
 8/17 Test  #8: format-impl-test .................   Passed    0.00 sec
      Start  9: ostream-test
```

[native-oracle-inventory.log](evidence/trial-001/native-oracle-inventory.log)

### trial-133 · fmtlib__fmt-2310 · state · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13564611727)。

F2P：0/1 通过；其余状态：`format-test`=failed。
P2P：16/16 通过；其余状态：全部通过。

[候选补丁](evidence/trial-133/candidate.patch)。

[native-oracle-build.log](evidence/trial-133/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-133/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-133/native-oracle-ctest.log)

从第 131 行起：

```text
[ RUN      ] format_test.format_nan
/src/test/format-test.cc:1275: Failure
Expected equality of these values:
  "  +nan"
  fmt::format("{:+06}", nan)
    Which is: "00+nan"
/src/test/format-test.cc:1276: Failure
Expected equality of these values:
  "+nan  "
  fmt::format("{:<+06}", nan)
```

从第 141 行起：

```text
    Which is: "+nan00"
/src/test/format-test.cc:1277: Failure
Expected equality of these values:
  " +nan "
  fmt::format("{:^+06}", nan)
    Which is: "0+nan0"
/src/test/format-test.cc:1278: Failure
Expected equality of these values:
  "  +nan"
  fmt::format("{:>+06}", nan)
```

从第 151 行起：

```text
    Which is: "00+nan"
/src/test/format-test.cc:1281: Failure
Expected equality of these values:
  "  -nan"
  fmt::format("{:+06}", -nan)
    Which is: "00-nan"
[  FAILED  ] format_test.format_nan (0 ms)
[ RUN      ] format_test.format_infinity
/src/test/format-test.cc:1297: Failure
Expected equality of these values:
```

从第 163 行起：

```text
    Which is: "00+inf"
/src/test/format-test.cc:1298: Failure
Expected equality of these values:
  "  -inf"
  fmt::format("{:+06}", -inf)
    Which is: "00-inf"
/src/test/format-test.cc:1299: Failure
Expected equality of these values:
  "+inf  "
  fmt::format("{:<+06}", inf)
```

[native-oracle-inventory.log](evidence/trial-133/native-oracle-inventory.log)

### trial-174 · fmtlib__fmt-2940 · combined · r2

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565529305)。

F2P：0/1 通过；其余状态：`ranges-test`=not_run。
P2P：0/19 通过；其余状态：`args-test`=not_run, `assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-fp-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `enforce-checks-test`=not_run, `format-impl-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `os-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `printf-test`=not_run, `scan-test`=not_run, `std-test`=not_run, `unicode-test`=not_run, `xchar-test`=not_run。

[候选补丁](evidence/trial-174/candidate.patch)。

[native-oracle-build.log](evidence/trial-174/native-oracle-build.log)

从第 38 行起：

```text
/src/test/ranges-test.cc:60:3:   required from here
/src/include/fmt/core.h:1707:7: error: static assertion failed: Cannot format an argument. To make type T formattable provide a formatter<T> specialization: https://fmt.dev/latest/api.html#udt
 1707 |       formattable,
      |       ^~~~~~~~~~~
/src/include/fmt/core.h:1707:7: note: ‘formattable’ evaluates to false
/src/include/fmt/core.h: In instantiation of ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_value(T&&) [with Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; T = std::pair<int, float>&]’:
/src/include/fmt/core.h:1727:29:   required from ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_arg(T&&) [with bool IS_PACKED = true; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; type <anonymous> = fmt::v8::detail::type::custom_type; T = std::pair<int, float>&; typename std::enable_if<IS_PACKED, int>::type <anonymous> = 0]’
/src/include/fmt/core.h:1851:77:   required from ‘fmt::v8::format_arg_store<Context, Args>::format_arg_store(T&& ...) [with T = {std::pair<int, float>&}; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; Args = {std::pair<int, float>}]’
/src/include/fmt/core.h:1868:38:   required from ‘constexpr fmt::v8::format_arg_store<Context, typename std::remove_cv<typename std::remove_reference<Args>::type>::type ...> fmt::v8::make_format_args(Args&& ...) [with Context = basic_format_context<appender, char>; Args = {std::pair<int, float>&}]’
/src/include/fmt/core.h:3137:44:   required from ‘std::string fmt::v8::format(format_string<T ...>, T&& ...) [with T = {std::pair<int, float>&}; std::string = std::__cxx11::basic_string<char>; format_string<T ...> = basic_format_string<char, std::pair<int, float>&>]’
```

从第 48 行起：

```text
/src/test/ranges-test.cc:85:3:   required from here
/src/include/fmt/core.h:1707:7: error: static assertion failed: Cannot format an argument. To make type T formattable provide a formatter<T> specialization: https://fmt.dev/latest/api.html#udt
/src/include/fmt/core.h:1707:7: note: ‘formattable’ evaluates to false
/src/include/fmt/core.h: In instantiation of ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_value(T&&) [with Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; T = std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&]’:
/src/include/fmt/core.h:1727:29:   required from ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_arg(T&&) [with bool IS_PACKED = true; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; type <anonymous> = fmt::v8::detail::type::custom_type; T = std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&; typename std::enable_if<IS_PACKED, int>::type <anonymous> = 0]’
/src/include/fmt/core.h:1851:77:   required from ‘fmt::v8::format_arg_store<Context, Args>::format_arg_store(T&& ...) [with T = {std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&}; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; Args = {std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>}]’
/src/include/fmt/core.h:1868:38:   required from ‘constexpr fmt::v8::format_arg_store<Context, typename std::remove_cv<typename std::remove_reference<Args>::type>::type ...> fmt::v8::make_format_args(Args&& ...) [with Context = basic_format_context<appender, char>; Args = {std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&}]’
/src/include/fmt/core.h:3137:44:   required from ‘std::string fmt::v8::format(format_string<T ...>, T&& ...) [with T = {std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&}; std::string = std::__cxx11::basic_string<char>; format_string<T ...> = basic_format_string<char, std::tuple<int, float, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, char>&>]’
/src/test/ranges-test.cc:93:3:   required from here
/src/include/fmt/core.h:1707:7: error: static assertion failed: Cannot format an argument. To make type T formattable provide a formatter<T> specialization: https://fmt.dev/latest/api.html#udt
```

从第 64 行起：

```text
/src/test/ranges-test.cc:94:3:   required from here
/src/include/fmt/core.h:1707:7: error: static assertion failed: Cannot format an argument. To make type T formattable provide a formatter<T> specialization: https://fmt.dev/latest/api.html#udt
/src/include/fmt/core.h:1707:7: note: ‘formattable’ evaluates to false
/src/include/fmt/core.h: In instantiation of ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_value(T&&) [with Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; T = tuple_like&]’:
/src/include/fmt/core.h:1727:29:   required from ‘fmt::v8::detail::value<Context> fmt::v8::detail::make_arg(T&&) [with bool IS_PACKED = true; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; type <anonymous> = fmt::v8::detail::type::custom_type; T = tuple_like&; typename std::enable_if<IS_PACKED, int>::type <anonymous> = 0]’
/src/include/fmt/core.h:1851:77:   required from ‘fmt::v8::format_arg_store<Context, Args>::format_arg_store(T&& ...) [with T = {tuple_like&}; Context = fmt::v8::basic_format_context<fmt::v8::appender, char>; Args = {tuple_like}]’
/src/include/fmt/core.h:1868:38:   required from ‘constexpr fmt::v8::format_arg_store<Context, typename std::remove_cv<typename std::remove_reference<Args>::type>::type ...> fmt::v8::make_format_args(Args&& ...) [with Context = basic_format_context<appender, char>; Args = {tuple_like&}]’
/src/include/fmt/core.h:3137:44:   required from ‘std::string fmt::v8::format(format_string<T ...>, T&& ...) [with T = {tuple_like&}; std::string = std::__cxx11::basic_string<char>; format_string<T ...> = basic_format_string<char, tuple_like&>]’
/src/test/ranges-test.cc:136:3:   required from here
/src/include/fmt/core.h:1707:7: error: static assertion failed: Cannot format an argument. To make type T formattable provide a formatter<T> specialization: https://fmt.dev/latest/api.html#udt
```

[native-oracle-configure.log](evidence/trial-174/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-174/native-oracle-inventory.log)

### trial-176 · fmtlib__fmt-3260 · baseline · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565194362)。

F2P：0/1 通过；其余状态：`chrono-test`=failed。
P2P：18/19 通过；其余状态：`compile-test`=failed。

[候选补丁](evidence/trial-176/candidate.patch)。

[native-oracle-build.log](evidence/trial-176/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-176/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-176/native-oracle-ctest.log)

从第 82 行起：

```text
The following tests FAILED:
	  3 - chrono-test (SEGFAULT)
	 10 - compile-test (SEGFAULT)
Errors while running CTest
```

[native-oracle-inventory.log](evidence/trial-176/native-oracle-inventory.log)

### trial-052 · fmtlib__fmt-3260 · combined · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560924391)。

F2P：0/1 通过；其余状态：`chrono-test`=failed。
P2P：18/19 通过；其余状态：`compile-test`=failed。

[候选补丁](evidence/trial-052/candidate.patch)。

[native-oracle-build.log](evidence/trial-052/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-052/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-052/native-oracle-ctest.log)

从第 82 行起：

```text
The following tests FAILED:
	  3 - chrono-test (SEGFAULT)
	 10 - compile-test (SEGFAULT)
Errors while running CTest
```

[native-oracle-inventory.log](evidence/trial-052/native-oracle-inventory.log)

### trial-082 · fmtlib__fmt-3260 · diagnostics · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13562846943)。

F2P：0/1 通过；其余状态：`chrono-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-082/candidate.patch)。

[native-oracle-build.log](evidence/trial-082/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-082/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-082/native-oracle-ctest.log)

从第 31 行起：

```text
[ RUN      ] chrono_test.tm_align
unknown file: Failure
C++ exception with description "invalid format" thrown in the test body.
[  FAILED  ] chrono_test.tm_align (0 ms)
[ RUN      ] chrono_test.tp_align
unknown file: Failure
C++ exception with description "invalid format" thrown in the test body.
[  FAILED  ] chrono_test.tp_align (0 ms)
[ RUN      ] chrono_test.format_specs
[       OK ] chrono_test.format_specs (0 ms)
```

从第 79 行起：

```text
[  PASSED  ] 27 tests.
[  FAILED  ] 2 tests, listed below:
[  FAILED  ] chrono_test.tm_align
[  FAILED  ] chrono_test.tp_align

 2 FAILED TESTS

      Start  4: color-test
 4/20 Test  #4: color-test .......................   Passed    0.00 sec
      Start  5: core-test
```

[native-oracle-inventory.log](evidence/trial-082/native-oracle-inventory.log)

### trial-126 · fmtlib__fmt-3732 · baseline · r1

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13564601263)。

F2P：0/1 通过；其余状态：`chrono-test`=not_run。
P2P：0/19 通过；其余状态：`args-test`=not_run, `assert-test`=not_run, `color-test`=not_run, `compile-fp-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `enforce-checks-test`=not_run, `format-impl-test`=not_run, `format-test`=not_run, `gtest-extra-test`=not_run, `os-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run, `std-test`=not_run, `unicode-test`=not_run, `xchar-test`=not_run。

[候选补丁](evidence/trial-126/candidate.patch)。

[native-oracle-build.log](evidence/trial-126/native-oracle-build.log)

从第 28 行起：

```text
/src/test/chrono-test.cc:433:3:   required from here
/usr/include/c++/13/ratio:100:47: error: static assertion failed: overflow in multiplication
  100 |       static_assert(__a0 * __b1 + __b0 * __a1 < (__c >> 1),
      |                     ~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~~
/usr/include/c++/13/ratio:100:47: note: the comparison reduces to ‘(20116567555200 < 2147483648)’
/usr/include/c++/13/ratio:105:21: error: static assertion failed: overflow in multiplication
  104 |       static_assert((__a0 * __b1 + __b0 * __a1) * __c
      |                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  105 |                     <= __INTMAX_MAX__ -  __b0 * __a0,
      |                     ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

从第 51 行起：

```text
/src/test/chrono-test.cc:433:3:   required from here
/usr/include/c++/13/ratio:109:29: error: overflow in constant expression [-fpermissive]
  109 |       static const intmax_t value = _Pn * _Qn;
      |                             ^~~~~
/usr/include/c++/13/ratio:109:29: error: overflow in constant expression [-fpermissive]
/src/include/fmt/chrono.h: In instantiation of ‘To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&) [with To = std::chrono::duration<unsigned int, std::ratio<86400> >; FromRep = unsigned int; FromPeriod = std::ratio<1, 1000000000000000000>; typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous> = 0; typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> = 0]’:
/src/include/fmt/chrono.h:450:53:   required from ‘To fmt::v10::detail::fmt_duration_cast(std::chrono::duration<_Rep, _Period>) [with To = std::chrono::duration<unsigned int, std::ratio<86400> >; FromRep = unsigned int; FromPeriod = std::ratio<1, 1000000000000000000>; typename std::enable_if<is_same_arithmetic_type<FromRep, typename To::rep>::value, int>::type <anonymous> = 0]’
/src/include/fmt/chrono.h:1892:41:   required from ‘void fmt::v10::detail::chrono_formatter<FormatContext, OutputIt, Rep, Period>::on_day_of_year() [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; OutputIt = std::back_insert_iterator<fmt::v10::basic_memory_buffer<char> >; Rep = int; Period = std::ratio<1, 1000000000000000000>]’
/src/include/fmt/chrono.h:767:29:   required from ‘constexpr const Char* fmt::v10::detail::parse_chrono_format(const Char*, const Char*, Handler&&) [with Char = char; Handler = chrono_formatter<fmt::v10::basic_format_context<fmt::v10::appender, char>, std::back_insert_iterator<fmt::v10::basic_memory_buffer<char> >, int, std::ratio<1, 1000000000000000000> >&]’
/src/include/fmt/chrono.h:2100:34:   required from ‘decltype (ctx.out()) fmt::v10::formatter<std::chrono::duration<_Rep1, _Period1>, Char>::format(std::chrono::duration<_Rep1, _Period1>, FormatContext&) const [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; Rep = int; Period = std::ratio<1, 1000000000000000000>; Char = char; decltype (ctx.out()) = fmt::v10::appender]’
```

从第 67 行起：

```text
/src/test/chrono-test.cc:433:3:   required from here
/src/include/fmt/chrono.h:200:25: error: ‘num’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  200 |   static_assert(Factor::num > 0, "num must be positive");
      |                         ^~~
/src/include/fmt/chrono.h:201:25: error: ‘den’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  201 |   static_assert(Factor::den > 0, "den must be positive");
      |                         ^~~
/src/include/fmt/chrono.h:209:42: error: ‘num’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  209 |                                 decltype(Factor::num)>::type;
      |                                          ^~~~~~
```

从第 76 行起：

```text
      |                                          ^~~~~~
/src/include/fmt/chrono.h:216:35: error: ‘num’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  216 |   if (detail::const_check(Factor::num != 1)) {
      |                                   ^~~
/src/include/fmt/chrono.h:217:70: error: ‘num’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  217 |     const auto max1 = detail::max_value<IntermediateRep>() / Factor::num;
      |                                                                      ^~~
/src/include/fmt/chrono.h:209:42: error: ‘num’ is not a member of ‘fmt::v10::safe_duration_cast::safe_duration_cast<std::chrono::duration<unsigned int, std::ratio<86400> >, unsigned int, std::ratio<1, 1000000000000000000> >(std::chrono::duration<unsigned int, std::ratio<1, 1000000000000000000> >, int&)::Factor’
  209 |                                 decltype(Factor::num)>::type;
      |                                          ^~~~~~
```

[native-oracle-configure.log](evidence/trial-126/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-126/native-oracle-inventory.log)

### trial-147 · fmtlib__fmt-3734 · combined · r2

冷评分：`EMPTY_CANDIDATE`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565002328)。

执行结束时未形成非空候选补丁，冷构建与测试保持未执行状态。

### trial-060 · fmtlib__fmt-3750 · combined · r1

冷评分：`ORACLE_BUILD_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13562306396)。

F2P：0/1 通过；其余状态：`format-test`=not_run。
P2P：0/19 通过；其余状态：`args-test`=not_run, `assert-test`=not_run, `chrono-test`=not_run, `color-test`=not_run, `compile-fp-test`=not_run, `compile-test`=not_run, `core-test`=not_run, `enforce-checks-test`=not_run, `format-impl-test`=not_run, `gtest-extra-test`=not_run, `os-test`=not_run, `ostream-test`=not_run, `posix-mock-test`=not_run, `printf-test`=not_run, `ranges-test`=not_run, `scan-test`=not_run, `std-test`=not_run, `unicode-test`=not_run, `xchar-test`=not_run。

[候选补丁](evidence/trial-060/candidate.patch)。

[native-oracle-build.log](evidence/trial-060/native-oracle-build.log)

从第 35 行起：

```text
/src/include/fmt/xchar.h:34:21:   required from here
/src/include/fmt/format.h:2184:22: error: no matching function for call to ‘fmt::v10::appender::appender(fmt::v10::basic_memory_buffer<wchar_t>&)’
 2184 |       detail::fill_n(appender(digits), to_unsigned(specs.precision - num_digits),
      |                      ^~~~~~~~~~~~~~~~
In file included from /usr/include/c++/13/bits/stl_algobase.h:67,
                 from /usr/include/c++/13/algorithm:60,
                 from /src/include/fmt/printf.h:11:
/usr/include/c++/13/bits/stl_iterator.h:713:7: note: candidate: ‘std::back_insert_iterator<_Container>::back_insert_iterator(_Container&) [with _Container = fmt::v10::detail::buffer<char>]’
  713 |       back_insert_iterator(_Container& __x)
      |       ^~~~~~~~~~~~~~~~~~~~
```

从第 77 行起：

```text
/src/include/fmt/core.h:1094:7: note:   no known conversion for argument 1 from ‘fmt::v10::basic_memory_buffer<wchar_t>’ to ‘fmt::v10::appender&&’
/src/include/fmt/format.h:2186:34: error: no matching function for call to ‘fmt::v10::appender::appender(fmt::v10::basic_memory_buffer<wchar_t>&)’
 2186 |     format_uint<BASE_BITS, Char>(appender(digits), value, num_digits, upper);
      |                                  ^~~~~~~~~~~~~~~~
/usr/include/c++/13/bits/stl_iterator.h:713:7: note: candidate: ‘std::back_insert_iterator<_Container>::back_insert_iterator(_Container&) [with _Container = fmt::v10::detail::buffer<char>]’
  713 |       back_insert_iterator(_Container& __x)
      |       ^~~~~~~~~~~~~~~~~~~~
/src/include/fmt/core.h:1098:58: note:   inherited here
 1098 |   using std::back_insert_iterator<detail::buffer<char>>::back_insert_iterator;
      |                                                          ^~~~~~~~~~~~~~~~~~~~
```

从第 120 行起：

```text
/src/include/fmt/xchar.h:34:21:   required from here
/src/include/fmt/format.h:2184:22: error: no matching function for call to ‘fmt::v10::appender::appender(fmt::v10::basic_memory_buffer<wchar_t>&)’
 2184 |       detail::fill_n(appender(digits), to_unsigned(specs.precision - num_digits),
      |                      ^~~~~~~~~~~~~~~~
/usr/include/c++/13/bits/stl_iterator.h:713:7: note: candidate: ‘std::back_insert_iterator<_Container>::back_insert_iterator(_Container&) [with _Container = fmt::v10::detail::buffer<char>]’
  713 |       back_insert_iterator(_Container& __x)
      |       ^~~~~~~~~~~~~~~~~~~~
/src/include/fmt/core.h:1098:58: note:   inherited here
 1098 |   using std::back_insert_iterator<detail::buffer<char>>::back_insert_iterator;
      |                                                          ^~~~~~~~~~~~~~~~~~~~
```

从第 158 行起：

```text
/src/include/fmt/core.h:1094:7: note:   no known conversion for argument 1 from ‘fmt::v10::basic_memory_buffer<wchar_t>’ to ‘fmt::v10::appender&&’
/src/include/fmt/format.h:2186:34: error: no matching function for call to ‘fmt::v10::appender::appender(fmt::v10::basic_memory_buffer<wchar_t>&)’
 2186 |     format_uint<BASE_BITS, Char>(appender(digits), value, num_digits, upper);
      |                                  ^~~~~~~~~~~~~~~~
/usr/include/c++/13/bits/stl_iterator.h:713:7: note: candidate: ‘std::back_insert_iterator<_Container>::back_insert_iterator(_Container&) [with _Container = fmt::v10::detail::buffer<char>]’
  713 |       back_insert_iterator(_Container& __x)
      |       ^~~~~~~~~~~~~~~~~~~~
/src/include/fmt/core.h:1098:58: note:   inherited here
 1098 |   using std::back_insert_iterator<detail::buffer<char>>::back_insert_iterator;
      |                                                          ^~~~~~~~~~~~~~~~~~~~
```

[native-oracle-configure.log](evidence/trial-060/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/trial-060/native-oracle-inventory.log)

### trial-017 · fmtlib__fmt-3819 · baseline · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560536801)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-017/candidate.patch)。

[native-oracle-build.log](evidence/trial-017/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-017/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-017/native-oracle-ctest.log)

从第 23 行起：

```text
[ RUN      ] args_test.named_with_manual_index
/src/test/args-test.cc:128: Failure
Expected equality of these values:
  "1 2 3 4 1"
  fmt::vformat("{0} {a1} {a2} {3} {0}", store)
    Which is: "1 2 3 3 1"
[  FAILED  ] args_test.named_with_manual_index (0 ms)
[ RUN      ] args_test.named_custom_format
[       OK ] args_test.named_custom_format (0 ms)
[ RUN      ] args_test.clear
```

从第 44 行起：

```text
[  PASSED  ] 13 tests.
[  FAILED  ] 1 test, listed below:
[  FAILED  ] args_test.named_with_manual_index

 1 FAILED TEST

      Start  2: base-test
 2/20 Test  #2: base-test ........................   Passed    0.00 sec
      Start  3: assert-test
 3/20 Test  #3: assert-test ......................   Passed    0.00 sec
```

[native-oracle-inventory.log](evidence/trial-017/native-oracle-inventory.log)

### trial-011 · fmtlib__fmt-3819 · baseline · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13560027451)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-011/candidate.patch)。

[native-oracle-build.log](evidence/trial-011/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-011/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-011/native-oracle-ctest.log)

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

[native-oracle-inventory.log](evidence/trial-011/native-oracle-inventory.log)

### trial-022 · fmtlib__fmt-3819 · combined · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13559879497)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-022/candidate.patch)。

[native-oracle-build.log](evidence/trial-022/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-022/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-022/native-oracle-ctest.log)

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

[native-oracle-inventory.log](evidence/trial-022/native-oracle-inventory.log)

### trial-171 · fmtlib__fmt-3819 · combined · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13565444136)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-171/candidate.patch)。

[native-oracle-build.log](evidence/trial-171/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-171/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-171/native-oracle-ctest.log)

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

[native-oracle-inventory.log](evidence/trial-171/native-oracle-inventory.log)

### trial-078 · fmtlib__fmt-3819 · dedup · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13562911664)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-078/candidate.patch)。

[native-oracle-build.log](evidence/trial-078/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-078/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-078/native-oracle-ctest.log)

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

[native-oracle-inventory.log](evidence/trial-078/native-oracle-inventory.log)

### trial-142 · fmtlib__fmt-3819 · dedup · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13564603364)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-142/candidate.patch)。

[native-oracle-build.log](evidence/trial-142/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-142/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-142/native-oracle-ctest.log)

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

[native-oracle-inventory.log](evidence/trial-142/native-oracle-inventory.log)

### trial-187 · fmtlib__fmt-3819 · diagnostics · r1

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13566257381)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-187/candidate.patch)。

[native-oracle-build.log](evidence/trial-187/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-187/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-187/native-oracle-ctest.log)

从第 29 行起：

```text
[ RUN      ] args_test.reserve
/src/test/args-test.cc:167: Failure
Expected equality of these values:
  "42 and 1.5"
  result
    Which is: "42 and cust=21910"
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

[native-oracle-inventory.log](evidence/trial-187/native-oracle-inventory.log)

### trial-058 · fmtlib__fmt-3819 · diagnostics · r2

冷评分：`ORACLE_TESTS_FAILED`；停止：`REQUEST_BUDGET_EXHAUSTED`；请求：24/24；原件核验：`verified`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42335967622/artifacts/13562465181)。

F2P：0/1 通过；其余状态：`args-test`=failed。
P2P：19/19 通过；其余状态：全部通过。

[候选补丁](evidence/trial-058/candidate.patch)。

[native-oracle-build.log](evidence/trial-058/native-oracle-build.log)

[native-oracle-configure.log](evidence/trial-058/native-oracle-configure.log)

[native-oracle-ctest.log](evidence/trial-058/native-oracle-ctest.log)

从第 29 行起：

```text
[ RUN      ] args_test.reserve
/src/test/args-test.cc:167: Failure
Expected equality of these values:
  "42 and 1.5"
  result
    Which is: "42 and 42"
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

[native-oracle-inventory.log](evidence/trial-058/native-oracle-inventory.log)
