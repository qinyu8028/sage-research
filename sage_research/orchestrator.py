import os, json

from sage_research.agents import Supervisor, Researcher, Writer
from sage_research.base import LLMClient
from sage_research.config import Config
from sage_research.context import HistoryCompactor, TokenCounter, ContextBuilder
from sage_research.graph import build_graph
from sage_research.library import LibraryManager
from sage_research.mcp import create_mcp_clients, register_mcp_tools
from sage_research.rag import Pipeline
from sage_research.search import SearchTool
from sage_research.tools import ToolRegistry, RAGTool, PaperReaderTool


class Orchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.llm_client = LLMClient(model=config.llm.model, timeout=config.llm.timeout)
        token_counter = TokenCounter()
        history_compactor = HistoryCompactor(llm_client=self.llm_client)
        self.context_builder = ContextBuilder(
            history_compactor=history_compactor,
            token_counter=token_counter,
        )
        self.rag_pipeline = Pipeline(data_dir=config.data_dir, llm_client=self.llm_client)
        self.mcp_clients = create_mcp_clients(
            os.path.join(self.config.config_dir, "mcp_servers.json")
        )
        tool_registry = ToolRegistry()
        register_mcp_tools(registry=tool_registry, clients=self.mcp_clients)

        brave_tool = tool_registry.tools["mcp__brave-search__brave_web_search"]
        tavily_tool = tool_registry.tools["mcp__tavily__tavily_search"]
        search_tool = SearchTool(brave_tool=brave_tool, tavily_tool=tavily_tool)
        
        download_tool = tool_registry.tools["mcp__paper-search__download_arxiv"]
        read_tool = tool_registry.tools["mcp__paper-search__read_arxiv_paper"]
        paper_reader_tool = PaperReaderTool(download_tool=download_tool, read_tool=read_tool)
        self.paper_reader = paper_reader_tool

        rag_tool = RAGTool(pipeline=self.rag_pipeline)
        
        pdfmux_tool = tool_registry.tools["mcp__pdfmux__convert_pdf"]
        self.pdfmux_tool = pdfmux_tool

        tool_registry.register_tool(search_tool)
        tool_registry.register_tool(paper_reader_tool)
        tool_registry.register_tool(rag_tool)

        with open(os.path.join(self.config.config_dir, "agents.json")) as f:
            agent_configs = json.load(f)

        whitelist = agent_configs["researcher"]["allowed_tools"]
        self.researcher_tools = tool_registry.get_tools(whitelist)
        
    def run_research(self, brief: str):
        supervisor = Supervisor(llm=self.llm_client, context_builder=self.context_builder, max_steps=self.config.max_steps)
        writer = Writer(llm=self.llm_client, context_builder=self.context_builder)

        # make sure that every researcher's history is independent
        def create_researcher(researcher_id: str = "R-?"):
            return Researcher(
                name=researcher_id,
                llm=self.llm_client,
                context_builder=self.context_builder,
                tool_list=self.researcher_tools,
                max_steps=self.config.max_steps,
            )

        graph = build_graph(supervisor, create_researcher, writer, self.rag_pipeline, self.config.max_rounds)
        graph_generator = graph.stream({"research_brief": brief})
        for event in graph_generator:
            yield event

    def create_library_manager(self) -> LibraryManager:
        manager = LibraryManager(
            data_dir=self.config.data_dir,
            paper_tool=self.paper_reader,
            pdfmux_tool=self.pdfmux_tool,
            pipeline=self.rag_pipeline,
        )
        return manager

    def close(self):
        self.paper_reader.cleanup()
        for client in self.mcp_clients:
            client.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()