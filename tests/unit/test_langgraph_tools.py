from fathom_play.tools import make_tool


def test_explicit_tool_invokes_function_without_decorator():
    tool = make_tool("add", "Adds values", lambda left, right: left + right)

    assert tool.invoke(left=2, right=3) == 5
    assert tool.name == "add"
    assert tool.description == "Adds values"
