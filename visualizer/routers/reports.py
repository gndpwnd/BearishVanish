"""
Reports Router - API endpoints for markdown reports
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
import traceback
import io

from routers.analyses import get_current_analysis_reader
from report_generator import MarkdownReportGenerator


router = APIRouter()


@router.get("/{strategy_name}", response_class=PlainTextResponse)
async def get_strategy_report(strategy_name: str):
    """
    Get comprehensive markdown report for a strategy
    
    Returns a detailed analysis report suitable for:
    - Exporting to files
    - Reviewing in markdown viewer
    - Sending to LLMs for analysis
    - Version control and documentation
    
    Args:
        strategy_name: Name of the strategy to report on
        
    Returns:
        Markdown-formatted string report
        
    Example:
        curl http://localhost:8000/api/v1/reports/My%20Strategy
    """
    try:
        reader = get_current_analysis_reader()
        
        # Verify strategy exists
        summary = reader.get_summary(strategy_name)
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Generate report
        generator = MarkdownReportGenerator(reader)
        report = generator.generate_full_report(strategy_name)
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating report: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )


@router.get("/{strategy_name}/summary", response_class=PlainTextResponse)
async def get_strategy_summary_report(strategy_name: str):
    """
    Get quick summary report for a strategy (faster, less detailed)
    
    Returns only the key metrics and executive summary
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Brief markdown report
    """
    try:
        reader = get_current_analysis_reader()
        
        # Verify strategy exists
        summary = reader.get_summary(strategy_name)
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Generate minimal report
        generator = MarkdownReportGenerator(reader)
        
        from io import StringIO
        report = StringIO()
        report.write(generator._generate_header(strategy_name))
        report.write(generator._generate_executive_summary(strategy_name))
        report.write(generator._generate_key_metrics(strategy_name))
        
        return report.getvalue()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating summary report: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary report: {str(e)}"
        )


@router.get("/{strategy_name}/performance", response_class=PlainTextResponse)
async def get_strategy_performance_report(strategy_name: str):
    """
    Get detailed performance analysis report
    
    Focuses on returns, metrics, and risk analysis
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Performance-focused markdown report
    """
    try:
        reader = get_current_analysis_reader()
        
        summary = reader.get_summary(strategy_name)
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        generator = MarkdownReportGenerator(reader)
        
        from io import StringIO
        report = StringIO()
        report.write(generator._generate_header(strategy_name))
        report.write(generator._generate_performance_analysis(strategy_name))
        report.write(generator._generate_risk_analysis(strategy_name))
        report.write(generator._generate_key_metrics(strategy_name))
        report.write(generator._generate_trade_analysis(strategy_name))
        
        return report.getvalue()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating performance report: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating performance report: {str(e)}"
        )


@router.get("/{strategy_name}/improvement", response_class=PlainTextResponse)
async def get_strategy_improvement_report(strategy_name: str):
    """
    Get improvement-focused report (issues and opportunities)
    
    Perfect for sending to LLMs for improvement suggestions
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Improvement-focused markdown report with LLM prompts
    """
    try:
        reader = get_current_analysis_reader()
        
        summary = reader.get_summary(strategy_name)
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        generator = MarkdownReportGenerator(reader)
        
        from io import StringIO
        report = StringIO()
        report.write(generator._generate_header(strategy_name))
        report.write(generator._generate_executive_summary(strategy_name))
        report.write(generator._generate_key_metrics(strategy_name))
        report.write(generator._generate_weaknesses_and_opportunities(strategy_name))
        report.write(generator._generate_recommendations(strategy_name))
        
        return report.getvalue()
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating improvement report: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating improvement report: {str(e)}"
        )


@router.get("/{strategy_name}/download")
async def download_strategy_report(strategy_name: str, report_type: str = "full"):
    """
    Download strategy report as markdown file with timestamp in filename
    
    The filename format is: {strategy_name}_{timestamp}.md
    where timestamp is from the analysis database
    
    Args:
        strategy_name: Name of the strategy
        report_type: Type of report (full, summary, performance, improvement)
        
    Returns:
        File download with proper Content-Disposition header
        
    Example:
        curl http://localhost:8000/api/v1/reports/My%20Strategy/download?report_type=full -o report.md
    """
    try:
        reader = get_current_analysis_reader()
        
        # Verify strategy exists
        summary = reader.get_summary(strategy_name)
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy '{strategy_name}' not found"
            )
        
        # Generate report based on type
        generator = MarkdownReportGenerator(reader)
        
        if report_type == "summary":
            from io import StringIO
            report = StringIO()
            report.write(generator._generate_header(strategy_name))
            report.write(generator._generate_executive_summary(strategy_name))
            report.write(generator._generate_key_metrics(strategy_name))
            content = report.getvalue()
        elif report_type == "performance":
            from io import StringIO
            report = StringIO()
            report.write(generator._generate_header(strategy_name))
            report.write(generator._generate_performance_analysis(strategy_name))
            report.write(generator._generate_risk_analysis(strategy_name))
            report.write(generator._generate_key_metrics(strategy_name))
            report.write(generator._generate_trade_analysis(strategy_name))
            content = report.getvalue()
        elif report_type == "improvement":
            from io import StringIO
            report = StringIO()
            report.write(generator._generate_header(strategy_name))
            report.write(generator._generate_executive_summary(strategy_name))
            report.write(generator._generate_key_metrics(strategy_name))
            report.write(generator._generate_weaknesses_and_opportunities(strategy_name))
            report.write(generator._generate_recommendations(strategy_name))
            content = report.getvalue()
        else:  # full (default)
            content = generator.generate_full_report(strategy_name)
        
        # Generate filename with timestamp
        db_timestamp = generator.get_db_timestamp()
        # Sanitize strategy name for filename
        safe_name = strategy_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{safe_name}_{db_timestamp}.md"
        
        # Create file-like object
        file_content = io.BytesIO(content.encode('utf-8'))
        
        return StreamingResponse(
            iter([file_content.getvalue()]),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading report: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading report: {str(e)}"
        )
