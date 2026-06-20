"""Human-readable stage output for graph execution."""

import logging
import time

logger = logging.getLogger("sage_research.display")


def _log(msg: str):
    logger.info(msg)


def format_review_verdict(note_review) -> str:
    failed = note_review.failed_criteria()
    if not failed:
        return f"verdict={note_review.verdict} (4/4 PASS)"
    lines = [f"verdict={note_review.verdict}"]
    for line in failed.split("\n"):
        lines.append(f"       {line}")
    return "\n".join(lines)


def print_stage_header(node_name: str, elapsed: float):
    _log(f"\n{'=' * 60}")
    _log(f"[{node_name}]  (elapsed {elapsed:.1f}s)")
    _log("=" * 60)


def print_plan(output):
    sub_questions = output.get("sub_questions", [])
    _log(f"  拆分出 {len(sub_questions)} 个子问题:")
    for i, sq in enumerate(sub_questions):
        _log(f"\n  [{i}] question: {sq.question}")
        _log(f"      rationale: {sq.rationale}")


def print_research(output):
    pairs = output.get("pending_review_pairs", [])
    for q, note in pairs:
        _log(f"  子问题: {q}")
        _log(f"  研究笔记 ({len(note)} 字符):")
        _log("  " + "-" * 50)
        for line in note.split("\n"):
            _log(f"  {line}")
        _log("  " + "-" * 50)


def print_review(output):
    rr = output.get("review_result")
    if rr:
        for i, nr in enumerate(rr.note_reviews):
            _log(f"  [{i}] {format_review_verdict(nr)}")
        if rr.missing_dimensions:
            _log(f"  missing_dimensions: {rr.missing_dimensions}")
    _log(f"  approved_pairs 新增: {len(output.get('approved_pairs', []))} 条")
    retry = output.get("retry_items", [])
    if retry:
        _log(f"  retry_items: {len(retry)} 条")
        for item in retry:
            _log(f"    - {item['sub_question'][:80]}")
    _log(f"  refine_round: {output.get('refine_round')}")


def print_write(output):
    report = output.get("final_report", "")
    _log(f"  报告长度: {len(report)} 字符")
    _log(f"\n{'=' * 60}")
    _log("最终报告:")
    _log("=" * 60)
    _log(report)


def stream_events(events):
    printers = {
        "plan_node": print_plan,
        "research_node": print_research,
        "review_node": print_review,
        "write_node": print_write,
    }
    t_start = time.time()
    for event in events:
        for node_name, output in event.items():
            elapsed = time.time() - t_start
            print_stage_header(node_name, elapsed)
            printer = printers.get(node_name)
            if printer:
                printer(output)
            else:
                _log(f"  output keys: {list(output.keys())}")
    elapsed = time.time() - t_start
    _log(f"\n总耗时: {elapsed:.1f}s")
