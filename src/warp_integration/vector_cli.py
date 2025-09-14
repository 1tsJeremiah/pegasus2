#!/usr/bin/env python3
"""
Warp Terminal Vector Database CLI Tool
=====================================

A command-line interface for managing vector databases in Warp Terminal.
This tool provides semantic search capabilities for commands, documentation,
and development workflows.

Usage:
    vector-cli --help
    vector-cli search "find files containing python"
    vector-cli add-docs ./docs/
    vector-cli semantic-help "git commit"
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import click
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.documents import Document
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("⚠️ Please install required dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Initialize Rich console for pretty output
console = Console()

class WarpVectorCLI:
    """CLI interface for vector database operations in Warp Terminal"""
    
    def __init__(self, collection_name: str = "warp_terminal", host: str = "localhost", port: int = 8000):
        """Initialize the vector CLI"""
        self.collection_name = collection_name
        self.host = host
        self.port = port
        
        try:
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings()
            
            # Connect to Chroma server
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Initialize vector store
            self.vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                client=self.client
            )
            
        except Exception as e:
            console.print(f"[red]❌ Failed to connect to vector database: {e}[/red]")
            console.print("[yellow]💡 Make sure Chroma is running: docker-compose -f docker/docker-compose.dev.yml up -d[/yellow]")
            sys.exit(1)
    
    def search(self, query: str, k: int = 5, show_scores: bool = False) -> List[Document]:
        """Semantic search in the vector database"""
        try:
            if show_scores:
                results = self.vectorstore.similarity_search_with_score(query, k=k)
                
                table = Table(title=f"🔍 Search Results for: '{query}'")
                table.add_column("Score", style="cyan")
                table.add_column("Content", style="white")
                table.add_column("Source", style="dim")
                
                for doc, score in results:
                    source = doc.metadata.get('source', 'Unknown') if doc.metadata else 'Unknown'
                    table.add_row(f"{score:.4f}", doc.page_content[:100] + "...", source)
                
                console.print(table)
                return [doc for doc, score in results]
            else:
                results = self.vectorstore.similarity_search(query, k=k)
                
                table = Table(title=f"🔍 Search Results for: '{query}'")
                table.add_column("Content", style="white")
                table.add_column("Source", style="dim")
                
                for doc in results:
                    source = doc.metadata.get('source', 'Unknown') if doc.metadata else 'Unknown'
                    table.add_row(doc.page_content[:100] + "...", source)
                
                console.print(table)
                return results
                
        except Exception as e:
            console.print(f"[red]❌ Search failed: {e}[/red]")
            return []
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a single document to the vector store"""
        try:
            doc = Document(page_content=content, metadata=metadata or {})
            self.vectorstore.add_documents([doc])
            console.print("[green]✅ Document added successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Failed to add document: {e}[/red]")
            return False
    
    def add_command_help(self, command: str, description: str, examples: List[str] = None) -> bool:
        """Add command help information to the vector store"""
        content = f"Command: {command}\nDescription: {description}"
        if examples:
            content += f"\nExamples: {'; '.join(examples)}"
        
        metadata = {
            "type": "command_help",
            "command": command,
            "category": "terminal"
        }
        
        return self.add_document(content, metadata)
    
    def semantic_help(self, query: str) -> None:
        """Provide semantic help based on query intent"""
        console.print(Panel(f"🤖 Finding help for: {query}", style="blue"))
        
        # Search for relevant help
        results = self.search(query, k=3)
        
        if not results:
            console.print("[yellow]No relevant help found. Try a different query.[/yellow]")
            return
        
        console.print("\n[bold]💡 Here's what I found:[/bold]")
        for i, doc in enumerate(results, 1):
            content = Text(f"{i}. {doc.page_content}")
            console.print(content)
            if doc.metadata:
                console.print(f"   [dim]Source: {doc.metadata.get('source', 'Unknown')}[/dim]")
            console.print()
    
    def status(self) -> None:
        """Show vector database status"""
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()
            
            status_panel = Panel(
                f"[green]✅ Connected to Chroma[/green]\n"
                f"Host: {self.host}:{self.port}\n"
                f"Collection: {self.collection_name}\n"
                f"Documents: {count}",
                title="📊 Vector Database Status"
            )
            console.print(status_panel)
            
        except Exception as e:
            console.print(f"[red]❌ Status check failed: {e}[/red]")


# CLI Commands
@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🚀 Warp Terminal Vector Database CLI
    
    Semantic search and AI-powered help for your terminal workflow.
    """
    pass


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=5, help='Number of results to return')
@click.option('--scores', '-s', is_flag=True, help='Show similarity scores')
def search(query: str, limit: int, scores: bool):
    """🔍 Semantic search in the vector database"""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]⚠️ Please set OPENAI_API_KEY environment variable[/red]")
        return
    
    vector_cli = WarpVectorCLI()
    vector_cli.search(query, k=limit, show_scores=scores)


@cli.command()
@click.argument('query')
def help(query: str):
    """🤖 Get semantic help for commands and workflows"""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]⚠️ Please set OPENAI_API_KEY environment variable[/red]")
        return
    
    vector_cli = WarpVectorCLI()
    vector_cli.semantic_help(query)


@cli.command()
@click.argument('content')
@click.option('--source', '-s', help='Source of the content')
@click.option('--category', '-c', help='Category of the content')
def add(content: str, source: Optional[str], category: Optional[str]):
    """📝 Add content to the vector database"""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]⚠️ Please set OPENAI_API_KEY environment variable[/red]")
        return
    
    metadata = {}
    if source:
        metadata['source'] = source
    if category:
        metadata['category'] = category
    
    vector_cli = WarpVectorCLI()
    vector_cli.add_document(content, metadata)


@cli.command()
@click.argument('command')
@click.argument('description')
@click.option('--examples', '-e', multiple=True, help='Usage examples')
def add_help(command: str, description: str, examples: tuple):
    """📚 Add command help to the vector database"""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]⚠️ Please set OPENAI_API_KEY environment variable[/red]")
        return
    
    vector_cli = WarpVectorCLI()
    vector_cli.add_command_help(command, description, list(examples))


@cli.command()
def status():
    """📊 Show vector database status"""
    vector_cli = WarpVectorCLI()
    vector_cli.status()


@cli.command()
def setup():
    """🔧 Setup initial help content"""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]⚠️ Please set OPENAI_API_KEY environment variable[/red]")
        return
    
    vector_cli = WarpVectorCLI()
    
    # Add some basic command help
    commands_help = [
        ("git commit", "Create a new commit with staged changes", ["git commit -m 'message'", "git commit --amend"]),
        ("docker ps", "List running Docker containers", ["docker ps", "docker ps -a"]),
        ("find", "Search for files and directories", ["find . -name '*.py'", "find /path -type f"]),
        ("grep", "Search text patterns in files", ["grep 'pattern' file.txt", "grep -r 'pattern' ."]),
        ("ls", "List directory contents", ["ls -la", "ls -lh"]),
        ("cd", "Change current directory", ["cd /path/to/dir", "cd ..", "cd ~"]),
        ("mkdir", "Create directories", ["mkdir new_dir", "mkdir -p path/to/dir"]),
        ("pip install", "Install Python packages", ["pip install package_name", "pip install -r requirements.txt"]),
    ]
    
    console.print("[blue]🔧 Setting up initial help content...[/blue]")
    
    for command, description, examples in commands_help:
        vector_cli.add_command_help(command, description, examples)
    
    console.print("[green]✅ Setup completed![/green]")


if __name__ == "__main__":
    cli()
