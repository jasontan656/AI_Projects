#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mail template converter

A simple preview converter that renders mail templates to browser-viewable HTML.

Quick usage (auto-saves to preview folder):
  python template_converter.py verification
  python template_converter.py welcome
  python template_converter.py marketing

Custom data:
  python template_converter.py verification --data my_data.json

Custom output path:
  python template_converter.py verification --output custom/my_preview.html
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

# sys.path.append 通过传入项目根目录路径添加到模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from shared_utilities.mail.TemplateManager import mail_template_manager
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)


def convert_template_to_preview(template_name: str, 
                                template_vars: Dict[str, Any], 
                                output_file: Optional[str] = None) -> str:
    """Render a mail template into a minimal preview HTML file and save it.

    Args:
        template_name: Template name (without extension)
        template_vars: Template variables
        output_file: Output path. If None, save under preview directory.

    Returns:
        Absolute path of the generated HTML file.
    """
    # mail_template_manager.render_template 方法渲染模板内容
    rendered_content = mail_template_manager.render_template(
        template_name,
        template_vars,
        'html'
    )
    
    # Generate a minimal preview HTML shell
    preview_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template_name} - mail preview</title>
</head>
<body style="margin: 0; padding: 20px; background-color: #f5f5f5; font-family: sans-serif;">
{rendered_content}
</body>
</html>"""
    
    # Determine output path
    if not output_file:
        # Get current directory
        current_dir = os.path.dirname(__file__)
        
        # Build preview directory path
        preview_dir = os.path.join(current_dir, 'preview')
        
        # Ensure preview directory exists
        os.makedirs(preview_dir, exist_ok=True)
        
        # Build output file path under preview
        output_file = os.path.join(preview_dir, f'{template_name}_converted.html')
    
    # Write the HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write content
        f.write(preview_html)
    
    # return 语句返回生成的文件路径
    return os.path.abspath(output_file)


def load_sample_data() -> Dict[str, Dict[str, Any]]:
    """Return default sample data for supported templates."""
    # return 语句返回包含各模板默认数据的字典
    return {
        "verification": {
            "verification_code": "123456",
            "expiry_minutes": 5,
            "is_test_mode": False
        },
        
        "welcome": {
            "user_name": "Test User",
            "dashboard_link": "https://careerbot.com/dashboard",
            "next_steps": ["Complete profile", "Take MBTI test", "Upload resume"]
        },
        
        "marketing": {
            "user_name": "User",
            "campaign_name": "New features released",
            "featured_content": {
                "title": "Featured capability",
                "description": "Feature description",
                "link": "https://example.com"
            },
            "content_items": [
                {"title": "Feature 1", "description": "Description 1"},
                {"title": "Feature 2", "description": "Description 2"}
            ],
            "cta_button": {
                "text": "View now",
                "link": "https://example.com"
            }
        }
    }


def main():
    """CLI entry: parse args and run conversion."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mail template converter')
    
    parser.add_argument('template', help='Template name (e.g., verification, welcome, marketing)')
    
    parser.add_argument('--data', '-d', help='Path to JSON data file (optional)')
    
    parser.add_argument('--output', '-o', help='Output HTML file path (optional)')
    
    # parser.parse_args 解析命令行参数
    args = parser.parse_args()
    
    # Load template variables
    if args.data:
        # Load from JSON if a data file is provided
        try:
            # Open JSON file
            with open(args.data, 'r', encoding='utf-8') as f:
                # Parse JSON into dict
                template_vars = json.load(f)
                
            print(f"OK data file loaded: {args.data}")
        except Exception as e:
            print(f"ERROR loading data file: {e}")
            return
    else:
        # Use default sample data
        sample_data = load_sample_data()
        
        # Pick template sample
        template_vars = sample_data.get(args.template, {})
        
        if not template_vars:
            print(f"WARN template '{args.template}' has no default data; using empty data")
            template_vars = {}
    
    # Execute conversion
    try:
        # Render to preview HTML
        output_path = convert_template_to_preview(
            args.template,
            template_vars,
            args.output
        )
        
        print(f"OK conversion completed")
        print(f"TEMPLATE: {args.template}")
        print(f"OUTPUT: {output_path}")
        print(f"INFO: Open the file in a browser to preview")
        
    except Exception as e:
        print(f"ERROR conversion failed: {e}")


def quick_convert(template_name: str, **kwargs) -> str:
    """Convenience function for converting a template to preview HTML in code."""
    # convert_template_to_preview 函数执行模板转换
    return convert_template_to_preview(template_name, kwargs)


if __name__ == "__main__":
    """Script entry point."""
    main()


# ========== Examples ==========
"""
Command line:

1) Convert using default sample data (auto-saved to preview folder):
   python template_converter.py verification
   -> preview/verification_converted.html

   python template_converter.py welcome
   -> preview/welcome_converted.html

   python template_converter.py marketing
   -> preview/marketing_converted.html

2) Use custom JSON data (saved under preview by default):
   python template_converter.py verification --data my_data.json
   -> preview/verification_converted.html

3) Specify custom output path:
   python template_converter.py welcome --output custom/welcome_preview.html
   -> custom/welcome_preview.html

In Python code:

from template_converter import quick_convert

output_file = quick_convert(
    'verification',
    verification_code='888888',
    expiry_minutes=10,
    is_test_mode=True
)
print(f"Preview file: {output_file}")
"""
