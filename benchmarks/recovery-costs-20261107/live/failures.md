# 恢复配对实验逐条失败

全部 4 对、8 条最终轨迹中有 3 条冷验收失败。

## pair-01-r2 · fmtlib__fmt-3732 · restart

冷评分 `ORACLE_BUILD_FAILED`；停止原因 `REQUEST_BUDGET_EXHAUSTED`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42342132692/artifacts/13568011186)。

[candidate.patch](evidence/pair-01-r2/restart/candidate.patch)

[native-oracle-build.log](evidence/pair-01-r2/restart/native-oracle-build.log)

第 28 行起：

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

第 51 行起：

```text
/src/test/chrono-test.cc:433:3:   required from here
/usr/include/c++/13/ratio:109:29: error: overflow in constant expression [-fpermissive]
  109 |       static const intmax_t value = _Pn * _Qn;
      |                             ^~~~~
/usr/include/c++/13/ratio:109:29: error: overflow in constant expression [-fpermissive]
/src/include/fmt/chrono.h: In instantiation of ‘To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&) [with To = std::chrono::duration<unsigned int, std::ratio<86400> >; FromRep = unsigned int; FromPeriod = std::ratio<1, 1000000000000000000>; typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous> = 0; typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> = 0]’:
/src/include/fmt/chrono.h:450:53:   required from ‘To fmt::v10::detail::fmt_duration_cast(std::chrono::duration<_Rep, _Period>) [with To = std::chrono::duration<unsigned int, std::ratio<86400> >; FromRep = unsigned int; FromPeriod = std::ratio<1, 1000000000000000000>; typename std::enable_if<is_same_arithmetic_type<FromRep, typename To::rep>::value, int>::type <anonymous> = 0]’
/src/include/fmt/chrono.h:1890:48:   required from ‘void fmt::v10::detail::chrono_formatter<FormatContext, OutputIt, Rep, Period>::on_day_of_year() [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; OutputIt = std::back_insert_iterator<fmt::v10::basic_memory_buffer<char> >; Rep = int; Period = std::ratio<1, 1000000000000000000>]’
/src/include/fmt/chrono.h:767:29:   required from ‘constexpr const Char* fmt::v10::detail::parse_chrono_format(const Char*, const Char*, Handler&&) [with Char = char; Handler = chrono_formatter<fmt::v10::basic_format_context<fmt::v10::appender, char>, std::back_insert_iterator<fmt::v10::basic_memory_buffer<char> >, int, std::ratio<1, 1000000000000000000> >&]’
/src/include/fmt/chrono.h:2097:34:   required from ‘decltype (ctx.out()) fmt::v10::formatter<std::chrono::duration<_Rep1, _Period1>, Char>::format(std::chrono::duration<_Rep1, _Period1>, FormatContext&) const [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; Rep = int; Period = std::ratio<1, 1000000000000000000>; Char = char; decltype (ctx.out()) = fmt::v10::appender]’
```

第 67 行起：

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

第 76 行起：

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

[native-oracle-configure.log](evidence/pair-01-r2/restart/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/pair-01-r2/restart/native-oracle-inventory.log)

## pair-02-r1 · fmtlib__fmt-3727 · resume

冷评分 `ORACLE_BUILD_FAILED`；停止原因 `REQUEST_BUDGET_EXHAUSTED`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42342132692/artifacts/13568207735)。

[candidate.patch](evidence/pair-02-r1/resume/candidate.patch)

[native-oracle-build.log](evidence/pair-02-r1/resume/native-oracle-build.log)

第 20 行起：

```text
/src/test/chrono-test.cc:904:3:   required from here
/src/include/fmt/chrono.h:2118:32: error: no matching function for call to ‘safe_duration_cast<std::chrono::seconds>(const std::chrono::duration<double, std::ratio<1, 3> >&, int&)’
 2117 |       auto epoch_seconds = safe_duration_cast::safe_duration_cast<
      |                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 2118 |           std::chrono::seconds>(epoch, ec);
      |           ~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous>, typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  191 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note:   template argument deduction/substitution failed:
```

第 31 行起：

```text
                 from /src/include/fmt/chrono.h:21:
/src/include/fmt/core.h:299:69: error: no type named ‘type’ in ‘struct std::enable_if<false, int>’
  299 | #  define FMT_ENABLE_IF(...) fmt::enable_if_t<(__VA_ARGS__), int> = 0
      |                                                                     ^
/src/include/fmt/chrono.h:189:11: note: in expansion of macro ‘FMT_ENABLE_IF’
  189 |           FMT_ENABLE_IF(std::is_integral<FromRep>::value),
      |           ^~~~~~~~~~~~~
/src/include/fmt/chrono.h:243:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_floating_point<From>::value, int>::type <anonymous>, typename std::enable_if<std::is_floating_point<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  243 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
```

第 41 行起：

```text
/src/include/fmt/chrono.h:243:4: note:   template argument deduction/substitution failed:
/src/include/fmt/core.h:299:69: error: no type named ‘type’ in ‘struct std::enable_if<false, int>’
  299 | #  define FMT_ENABLE_IF(...) fmt::enable_if_t<(__VA_ARGS__), int> = 0
      |                                                                     ^
/src/include/fmt/chrono.h:242:11: note: in expansion of macro ‘FMT_ENABLE_IF’
  242 |           FMT_ENABLE_IF(std::is_floating_point<typename To::rep>::value)>
      |           ^~~~~~~~~~~~~
/src/include/fmt/chrono.h: In instantiation of ‘decltype (ctx.out()) fmt::v10::formatter<std::chrono::time_point<std::chrono::_V2::system_clock, Duration>, Char>::format(std::chrono::time_point<std::chrono::_V2::system_clock, Duration>, FormatContext&) const [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; Char = char; Duration = std::chrono::duration<double>; decltype (ctx.out()) = fmt::v10::appender]’:
/src/include/fmt/core.h:1322:28:   required from ‘static void fmt::v10::detail::value<Context>::format_custom_arg(void*, typename Context::parse_context_type&, Context&) [with T = std::chrono::time_point<std::chrono::_V2::system_clock, std::chrono::duration<double> >; Formatter = fmt::v10::formatter<std::chrono::time_point<std::chrono::_V2::system_clock, std::chrono::duration<double> >, char, void>; Context = fmt::v10::basic_format_context<fmt::v10::appender, char>; typename Context::parse_context_type = fmt::v10::basic_format_parse_context<char>]’
/src/include/fmt/core.h:1304:19:   required from ‘fmt::v10::detail::value<Context>::value(T&) [with T = const std::chrono::time_point<std::chrono::_V2::system_clock, std::chrono::duration<double> >; Context = fmt::v10::basic_format_context<fmt::v10::appender, char>]’
```

第 55 行起：

```text
/src/test/chrono-test.cc:915:3:   required from here
/src/include/fmt/chrono.h:2118:32: error: no matching function for call to ‘safe_duration_cast<std::chrono::seconds>(const std::chrono::duration<double>&, int&)’
 2117 |       auto epoch_seconds = safe_duration_cast::safe_duration_cast<
      |                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 2118 |           std::chrono::seconds>(epoch, ec);
      |           ~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous>, typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  191 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note:   template argument deduction/substitution failed:
```

[native-oracle-configure.log](evidence/pair-02-r1/resume/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/pair-02-r1/resume/native-oracle-inventory.log)

## pair-02-r1 · fmtlib__fmt-3727 · restart

冷评分 `ORACLE_BUILD_FAILED`；停止原因 `REQUEST_BUDGET_EXHAUSTED`。

[完整原始轨迹](https://github.com/lilong555/ReproPatch/actions/runs/42342132692/artifacts/13568207735)。

[candidate.patch](evidence/pair-02-r1/restart/candidate.patch)

[native-oracle-build.log](evidence/pair-02-r1/restart/native-oracle-build.log)

第 21 行起：

```text
/src/test/chrono-test.cc:904:3:   required from here
/src/include/fmt/chrono.h:1628:53: error: no matching function for call to ‘safe_duration_cast<std::chrono::duration<long int, std::ratio<1, 1> > >(std::chrono::duration<double, std::ratio<1, 3> >&, int&)’
 1628 |   To to = safe_duration_cast::safe_duration_cast<To>(from, ec);
      |           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous>, typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  191 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note:   template argument deduction/substitution failed:
In file included from /src/include/fmt/format.h:49,
                 from /src/include/fmt/chrono.h:21:
```

第 30 行起：

```text
                 from /src/include/fmt/chrono.h:21:
/src/include/fmt/core.h:299:69: error: no type named ‘type’ in ‘struct std::enable_if<false, int>’
  299 | #  define FMT_ENABLE_IF(...) fmt::enable_if_t<(__VA_ARGS__), int> = 0
      |                                                                     ^
/src/include/fmt/chrono.h:189:11: note: in expansion of macro ‘FMT_ENABLE_IF’
  189 |           FMT_ENABLE_IF(std::is_integral<FromRep>::value),
      |           ^~~~~~~~~~~~~
/src/include/fmt/chrono.h:243:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_floating_point<From>::value, int>::type <anonymous>, typename std::enable_if<std::is_floating_point<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  243 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
```

第 40 行起：

```text
/src/include/fmt/chrono.h:243:4: note:   template argument deduction/substitution failed:
/src/include/fmt/core.h:299:69: error: no type named ‘type’ in ‘struct std::enable_if<false, int>’
  299 | #  define FMT_ENABLE_IF(...) fmt::enable_if_t<(__VA_ARGS__), int> = 0
      |                                                                     ^
/src/include/fmt/chrono.h:242:11: note: in expansion of macro ‘FMT_ENABLE_IF’
  242 |           FMT_ENABLE_IF(std::is_floating_point<typename To::rep>::value)>
      |           ^~~~~~~~~~~~~
/src/include/fmt/chrono.h: In instantiation of ‘To fmt::v10::detail::fmt_safe_duration_cast(std::chrono::duration<_Rep, _Period>) [with To = std::chrono::duration<long int>; FromRep = double; FromPeriod = std::ratio<1>]’:
/src/include/fmt/chrono.h:2100:32:   required from ‘decltype (ctx.out()) fmt::v10::formatter<std::chrono::time_point<std::chrono::_V2::system_clock, Duration>, Char>::format(std::chrono::time_point<std::chrono::_V2::system_clock, Duration>, FormatContext&) const [with FormatContext = fmt::v10::basic_format_context<fmt::v10::appender, char>; Char = char; Duration = std::chrono::duration<double>; decltype (ctx.out()) = fmt::v10::appender]’
/src/include/fmt/core.h:1322:28:   required from ‘static void fmt::v10::detail::value<Context>::format_custom_arg(void*, typename Context::parse_context_type&, Context&) [with T = std::chrono::time_point<std::chrono::_V2::system_clock, std::chrono::duration<double> >; Formatter = fmt::v10::formatter<std::chrono::time_point<std::chrono::_V2::system_clock, std::chrono::duration<double> >, char, void>; Context = fmt::v10::basic_format_context<fmt::v10::appender, char>; typename Context::parse_context_type = fmt::v10::basic_format_parse_context<char>]’
```

第 55 行起：

```text
/src/test/chrono-test.cc:915:3:   required from here
/src/include/fmt/chrono.h:1628:53: error: no matching function for call to ‘safe_duration_cast<std::chrono::duration<long int, std::ratio<1, 1> > >(std::chrono::duration<double>&, int&)’
 1628 |   To to = safe_duration_cast::safe_duration_cast<To>(from, ec);
      |           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note: candidate: ‘template<class To, class FromRep, class FromPeriod, typename std::enable_if<std::is_integral<_Size>::value, int>::type <anonymous>, typename std::enable_if<std::is_integral<typename To::rep>::value, int>::type <anonymous> > To fmt::v10::safe_duration_cast::safe_duration_cast(std::chrono::duration<_Rep, _Period>, int&)’
  191 | To safe_duration_cast(std::chrono::duration<FromRep, FromPeriod> from,
      |    ^~~~~~~~~~~~~~~~~~
/src/include/fmt/chrono.h:191:4: note:   template argument deduction/substitution failed:
/src/include/fmt/core.h:299:69: error: no type named ‘type’ in ‘struct std::enable_if<false, int>’
  299 | #  define FMT_ENABLE_IF(...) fmt::enable_if_t<(__VA_ARGS__), int> = 0
```

[native-oracle-configure.log](evidence/pair-02-r1/restart/native-oracle-configure.log)

[native-oracle-inventory.log](evidence/pair-02-r1/restart/native-oracle-inventory.log)
