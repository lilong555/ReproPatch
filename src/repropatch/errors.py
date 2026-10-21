class ReproPatchError(Exception):
    """A user-facing, non-secret error."""


class PolicyError(ReproPatchError):
    """An attempted tool action violates the task policy."""


class InfrastructureError(ReproPatchError):
    """Execution infrastructure failed; this is not a test failure."""


class SourceChanged(InfrastructureError):
    """宿主独占源码或其控制元数据不再符合已记录的不变量。"""


class PatchRejected(PolicyError):
    """候选未满足文件范围、模式、文本或字节往返契约。"""


class AuditLimit(InfrastructureError):
    """审计预算耗尽，必须停止新增执行并保存最终诊断。"""


class CleanupUnconfirmed(InfrastructureError):
    """无法证明所属容器已经删除，禁止继续执行或成功验收。"""


class ExecutionError(InfrastructureError):
    """Docker 执行或观察不确定，不能当作普通测试失败。"""


class OperationDeadline(ReproPatchError):
    """受控同步操作耗尽所属 Agent 阶段时间。"""


class StateReadError(InfrastructureError):
    """既有审计无法读取；不得创建新库或由派生文件替代。"""


class StateWriteError(InfrastructureError):
    """事件事务失败；不得声称对应事实已经提交。"""


class ArtifactExportError(InfrastructureError):
    """派生产物导出失败；已提交的 Run 结局保持不变。"""


class HarnessPause(ReproPatchError):
    """已提交完整输入边界的受控暂停；不是取消或最终结局。"""
