#!/usr/bin/env python3
"""
Analyze LangSmith traces for the Netbox Chatbox application.

This script processes trace JSON files fetched from LangSmith and generates
comprehensive insights about agent performance, tool usage, and query patterns.

Usage:
    python analyze_traces.py [trace_directory]

Arguments:
    trace_directory - Directory containing trace JSON files (default: ./langsmith-traces)
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any
from datetime import datetime


def load_traces(trace_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all trace JSON files from directory.

    Args:
        trace_dir: Path to directory containing trace JSON files.

    Returns:
        list[dict]: List of trace data dictionaries.
    """
    traces = []
    for json_file in sorted(trace_dir.glob("*.json")):
        try:
            with open(json_file, 'r') as f:
                trace_data = json.load(f)
                traces.append({
                    'id': json_file.stem,
                    'file': json_file.name,
                    'messages': trace_data  # Messages-based format
                })
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Failed to parse {json_file.name}: {e}")
            continue
    return traces


def analyze_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a single trace and extract metrics.

    Args:
        trace: Trace data dictionary with messages.

    Returns:
        dict: Analysis results with metrics.
    """
    messages = trace['messages']

    analysis = {
        'trace_id': trace['id'],
        'file': trace['file'],
        'total_messages': len(messages),
        'user_queries': [],
        'tool_calls': [],
        'tool_call_count': 0,
        'assistant_responses': 0,
        'completed': False,
        'tools_used': set()
    }

    for msg in messages:
        role = msg.get('role')

        if role == 'user':
            content = msg.get('content', '')
            if content:
                analysis['user_queries'].append(content)

        elif role == 'assistant':
            # Check for tool calls
            if msg.get('tool_calls'):
                tool_calls = msg.get('tool_calls', [])
                analysis['tool_call_count'] += len(tool_calls)
                for tc in tool_calls:
                    tool_name = tc.get('function', {}).get('name', 'unknown')
                    analysis['tools_used'].add(tool_name)
                    analysis['tool_calls'].append({
                        'tool': tool_name,
                        'args': tc.get('function', {}).get('arguments', '')
                    })

            # Check for responses
            if msg.get('content'):
                analysis['assistant_responses'] += 1
                analysis['completed'] = True

    analysis['tools_used'] = list(analysis['tools_used'])
    return analysis


def generate_report(traces: List[Dict[str, Any]], project_uuid: str) -> str:
    """
    Generate comprehensive analysis report.

    Args:
        traces: List of trace data dictionaries.
        project_uuid: LangSmith project UUID.

    Returns:
        str: Markdown-formatted analysis report.
    """
    # Analyze all traces
    analyses = [analyze_trace(t) for t in traces]

    # Aggregate statistics
    total_traces = len(traces)
    completed_traces = sum(1 for a in analyses if a['completed'])
    incomplete_traces = total_traces - completed_traces

    # Tool usage statistics
    tool_counter = Counter()
    total_tool_calls = 0
    all_queries = []

    for analysis in analyses:
        for tool in analysis['tools_used']:
            tool_counter[tool] += 1
        total_tool_calls += analysis['tool_call_count']
        all_queries.extend(analysis['user_queries'])

    # Generate markdown report
    report = f"""# LangSmith Trace Analysis Report
## Netbox Chatbox Application

### Project Information
- **Project UUID**: `{project_uuid}`
- **Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Traces Analyzed**: {total_traces}

---

## Executive Summary

### Completion Status
- **Total Traces**: {total_traces}
- **Completed**: {completed_traces} ({completed_traces/total_traces*100 if total_traces > 0 else 0:.1f}%)
- **Incomplete**: {incomplete_traces} ({incomplete_traces/total_traces*100 if total_traces > 0 else 0:.1f}%)

### Tool Usage
- **Total Tool Calls**: {total_tool_calls}
- **Average Tool Calls per Trace**: {total_tool_calls/total_traces if total_traces > 0 else 0:.1f}
- **Unique Tools Used**: {len(tool_counter)}

### Query Stats
- **Unique User Queries**: {len([q for q in all_queries if q])}

---

## Tool Usage Analysis

### Most Frequently Used Tools
"""

    if tool_counter:
        for tool, count in tool_counter.most_common(10):
            percentage = (count / total_traces) * 100 if total_traces > 0 else 0
            report += f"- **{tool}**: {count} times ({percentage:.1f}% of traces)\n"
    else:
        report += "- No tool usage detected\n"

    report += f"""
---

## Sample User Queries

"""

    if all_queries:
        for i, query in enumerate([q for q in all_queries if q][:10], 1):
            report += f"{i}. \"{query}\"\n"
    else:
        report += "- No queries extracted\n"

    report += f"""
---

## Performance Insights

### Key Findings

#### ✅ Strengths
1. **Completion Rate**: {completed_traces/total_traces*100 if total_traces > 0 else 0:.1f}% of traces completed successfully
2. **Tool Integration**: Agent successfully uses {len(tool_counter)} unique Netbox MCP tools
3. **Message Efficiency**: Average {sum(a['total_messages'] for a in analyses)/total_traces if total_traces > 0 else 0:.1f} messages per conversation

#### ⚠️ Areas for Improvement
"""

    if incomplete_traces > 0:
        report += f"1. **Incomplete Traces**: {incomplete_traces} traces didn't complete ({incomplete_traces/total_traces*100 if total_traces > 0 else 0:.1f}%)\n"

    if total_tool_calls / total_traces > 5 if total_traces > 0 else False:
        report += f"2. **Tool Call Efficiency**: High average tool calls ({total_tool_calls/total_traces:.1f}) per trace\n"

    report += f"""
---

## Recommendations

### Immediate Actions
1. **Monitor Error Patterns**: Review failed traces to identify common failure modes
2. **Optimize Tool Calls**: Consider caching or batching for frequently used queries
3. **Token Optimization**: Implement response streaming for long outputs

### Future Enhancements
1. **Add Retry Logic**: Implement automatic retry for failed tool calls
2. **Query Classification**: Pre-classify queries to optimize tool selection
3. **Response Caching**: Cache common query results to reduce latency

---

## Detailed Trace Breakdown

"""

    for i, analysis in enumerate(analyses[:20], 1):  # Show first 20 traces
        status = '✅ Completed' if analysis['completed'] else '⏳ Incomplete'
        query = analysis['user_queries'][0] if analysis['user_queries'] else 'N/A'

        report += f"""### Trace {i}: {analysis['trace_id'][:24]}...
- **File**: {analysis['file']}
- **User Query**: {query}
- **Status**: {status}
- **Messages**: {analysis['total_messages']}
- **Tool Calls**: {len(analysis['tool_calls'])}
- **Tools Used**: {', '.join(analysis['tools_used']) if analysis['tools_used'] else 'None'}

"""

    if total_traces > 20:
        report += f"\n*... and {total_traces - 20} more traces*\n"

    report += f"""
---

## Data Summary

### Trace Files
- **Directory**: `./langsmith-traces/`
- **Total Files**: {total_traces}
- **Total Size**: {sum(f.stat().st_size for f in Path('./langsmith-traces').glob('*.json')) / 1024 if Path('./langsmith-traces').exists() else 0:.1f} KB

### Analysis Metadata
- **Generated**: {datetime.now().isoformat()}
- **Tool**: analyze_traces.py
- **Project**: netbox-chatbox

---

*For more details, view individual trace files or visit [LangSmith Dashboard](https://smith.langchain.com)*
"""

    return report


def main():
    """Main analysis function."""
    # Configuration
    import os
    project_uuid = os.getenv('LANGCHAIN_PROJECT_UUID', 'your-project-uuid')
    trace_dir = Path(sys.argv[1] if len(sys.argv) > 1 else './langsmith-traces')

    if not trace_dir.exists():
        print(f"❌ Error: Trace directory {trace_dir} not found")
        print(f"\nRun './fetch_traces.sh' first to download traces")
        return 1

    print(f"🔍 Loading traces from {trace_dir}...")
    traces = load_traces(trace_dir)

    if not traces:
        print(f"❌ No traces found in {trace_dir}")
        print(f"\nRun './fetch_traces.sh' to download traces")
        return 1

    print(f"✅ Loaded {len(traces)} traces")
    print("📊 Generating analysis report...")

    report = generate_report(traces, project_uuid)

    # Save report
    report_path = Path('./trace_analysis_report.md')
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n✅ Analysis complete!")
    print(f"📄 Report saved to: {report_path}")
    print(f"\n" + "=" * 70)
    print(report[:500] + "...\n")
    print("=" * 70)
    print(f"\nView full report: cat {report_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
