from langchain_core.tools import tool


@tool
def python_calculator(expression: str) -> str:
    """
    安全执行 Python 数学表达式，用于计算增长率、比率、平均值等。
    支持: +, -, *, /, //, %, **, round(), abs(), min(), max(), sum()

    Args:
        expression: Python 数学表达式
                    例: "round((17.79 - 14.72) / 14.72 * 100, 2)"
                    例: "sum([3.2, 4.1, 2.8]) / 3"
    """
    allowed_names = {
        "round": round,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"[Calculator error] {e}"
