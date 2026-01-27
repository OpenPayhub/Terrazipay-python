import sys
import inspect
import traceback


def error_context(depth=5):
    """
    Captures the context of an exception, including local variables (parameters)
    and the call stack leading up to the error.

    Args:
        depth (int): How many steps back in the stack to record.

    Returns:
        str: A formatted string containing stack trace and local variables.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()

    if not exc_traceback:
        return "No active exception found."

    # Get the basic traceback information
    tb_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
    report = ["--- Exception Context Report ---"]
    report.append("".join(tb_details))

    report.append("\n--- Stack Local Variables (Deep Dive) ---")

    # Iterate through the stack frames
    # We use inspect to get local variables from each frame in the traceback
    current_traceback = exc_traceback
    stack_count = 0

    while current_traceback and stack_count < depth:
        frame = current_traceback.tb_frame
        info = inspect.getframeinfo(frame)

        report.append(
            f'Level {stack_count}: File "{info.filename}", line {info.lineno}, in {info.function}'
        )

        # Capture local variables (including function arguments)
        locals_map = frame.f_locals
        if locals_map:
            for var_name, var_value in locals_map.items():
                # We use repr() to get a string representation, but truncate if too long
                val_str = repr(var_value)
                if len(val_str) > 100:
                    val_str = val_str[:97] + "..."
                report.append(f"    {var_name} = {val_str}")
        else:
            report.append("    (No local variables)")

        current_traceback = current_traceback.tb_next
        stack_count += 1

    return "\n".join(report)
