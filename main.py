import argparse
import json
import logging
import os

from sage_research.base import TestAgent, setup_logging
from sage_research.context import ContextBuilder, TokenCounter, HistoryCompactor
from sage_research.graph import build_graph
from sage_research.rag import Pipeline
from sage_research.tools import ToolRegistry, RAGTool
from sage_research.tools.tool_paper import PaperReaderTool
from sage_research.mcp import create_mcp_clients, register_mcp_tools
from sage_research.agents import Clarifier, Supervisor, Writer, Researcher
from sage_research.search import SearchTool
from sage_research.config import Config

logger = logging.getLogger("sage_research.main")


def parse_args():
    parser = argparse.ArgumentParser(description="SAGE Research: 自主多 Agent 研究系统")
    parser.add_argument("query", nargs="?", default=None, help="研究问题（不提供则交互输入）")
    parser.add_argument("--model", default=None, help="LLM 模型名称")
    parser.add_argument("--max-rounds", type=int, default=None, help="最大审查轮数")
    parser.add_argument("--max-steps", type=int, default=None, help="Researcher 最大搜索步数")
    parser.add_argument("--timeout", type=int, default=None, help="LLM 调用超时(秒)")
    parser.add_argument("--data-dir", default=None, help="数据目录路径")
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()
    config = Config()

    if args.model:
        config.llm.model = args.model
    if args.max_rounds:
        config.max_rounds = args.max_rounds
    if args.max_steps:
        config.max_steps = args.max_steps
    if args.timeout:
        config.llm.timeout = args.timeout
    if args.data_dir:
        config.data_dir = args.data_dir

    llm = TestAgent(model=config.llm.model, timeout=config.llm.timeout)

    token_counter = TokenCounter()
    history_compactor = HistoryCompactor(
        llm_client=llm,
        token_counter=token_counter,
    )
    # TODO: add memory system
    context_builder = ContextBuilder(
        history_compactor=history_compactor,
        token_counter=token_counter,
        max_tokens=config.context.max_tokens,
        reserve_ratio=config.context.reserve_ratio,
    )

    pipeline = Pipeline(data_dir=config.data_dir, llm_client=llm)

    clients = create_mcp_clients(os.path.join(config.config_dir, "mcp_servers.json"))
    try:
        registry = ToolRegistry()
        register_mcp_tools(registry, clients)

        # search tool fallback integration
        brave_tool = registry.tools["mcp__brave-search__brave_web_search"]
        tavily_tool = registry.tools["mcp__tavily__tavily_search"]
        registry.register_tool(SearchTool(brave_tool, tavily_tool))

        # self-defined tools
        registry.register_tool(RAGTool(pipeline))

        download_tool = registry.tools["mcp__paper-search__download_arxiv"]
        read_tool = registry.tools["mcp__paper-search__read_arxiv_paper"]
        paper_reader = PaperReaderTool(download_tool, read_tool)
        registry.register_tool(paper_reader)

        with open(os.path.join(config.config_dir, "agents.json")) as f:
            agent_configs = json.load(f)
        researcher_whitelist = agent_configs["researcher"]["allowed_tools"]
        researcher_tools = registry.get_tools(researcher_whitelist)

        raw_query = args.query or input("请输入研究问题: ")
        clarifier = Clarifier(llm=llm)
        research_brief = clarifier.run(raw_query)

        supervisor = Supervisor(llm=llm, context_builder=context_builder, max_steps=config.max_steps)
        writer = Writer(llm=llm, context_builder=context_builder)

        # make sure that every researcher's history is independent
        def create_researcher(researcher_id: str = "R-?"):
            return Researcher(
                name=researcher_id,
                llm=llm,
                context_builder=context_builder,
                tool_list=researcher_tools,
                max_steps=config.max_steps,
            )

        graph = build_graph(supervisor, create_researcher, writer, pipeline, config.max_rounds)
        result = graph.invoke({"research_brief": research_brief})
        print(result["final_report"])

    finally:
        paper_reader.cleanup()
        for client in clients:
            client.disconnect()
        total_tokens = llm.total_prompt_tokens + llm.total_completion_tokens
        logger.info("统计: %d 次调用, tokens=%d(in:%d+out:%d)", llm.total_calls, total_tokens, llm.total_prompt_tokens, llm.total_completion_tokens)
        print(f"\n--- 统计 ---")
        print(f"LLM 调用: {llm.total_calls} 次")
        print(f"Token: {total_tokens} (in:{llm.total_prompt_tokens} + out:{llm.total_completion_tokens})")


if __name__ == "__main__":
    main()
