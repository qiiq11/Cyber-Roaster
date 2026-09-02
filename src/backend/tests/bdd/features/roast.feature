Feature: 代码幽默评审
  作为一个开发者
  我想提交代码片段并得到幽默评审
  以便在笑声中获得改进建议

  Scenario: 提交合法代码获得评审
    Given 我提交了一段合法的 Python 代码
    When 我调用评审接口
    Then 接口返回 200 状态码
    And 响应包含 roast_text 字段
    And 响应包含 chaos_score 字段
    And chaos_score 在 0 到 100 之间

  Scenario: 提交空代码被拒绝
    Given 我提交一段空代码
    When 我调用评审接口
    Then 接口返回 422 状态码

  Scenario: 统计接口反映评审数量
    Given 我提交了一段合法的 Python 代码
    When 我调用评审接口
    And 我调用统计接口
    Then 统计接口返回 total_analyses 为 1
