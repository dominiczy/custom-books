"""
Example prompts and usage patterns for document processing.
"""

from typing import Dict, List


def get_example_prompts() -> Dict[str, str]:
    """
    Get a dictionary of example prompts for different use cases.
    
    Returns:
        Dictionary mapping prompt names to prompt text
    """
    return {
        "chinese_text_processing": """
Process this Chinese text and provide:

1. **Full English Translation**: Translate the entire content into fluent, natural English
2. **Key Concepts Summary**: List and explain the main philosophical, cultural, or literary concepts
3. **Cultural Context**: Provide background information about historical/cultural significance
4. **Character Analysis** (if applicable): Break down important Chinese characters and their meanings
5. **Modern Relevance**: Explain how these teachings/concepts apply to modern life

Format the output as clear, well-structured markdown with proper headers and bullet points.
Make it comprehensive yet accessible to English readers unfamiliar with Chinese culture.
""",
        
        "academic_synthesis": """
Create a comprehensive academic synthesis of the provided materials:

1. **Executive Summary**: 2-3 paragraph overview of main themes and findings
2. **Key Arguments**: Identify and analyze the primary arguments presented
3. **Theoretical Framework**: Outline the theoretical approaches used
4. **Methodology Analysis**: Examine research methods and their effectiveness
5. **Critical Evaluation**: Assess strengths, limitations, and potential biases
6. **Comparative Analysis**: Compare and contrast different sources/viewpoints
7. **Implications**: Discuss theoretical and practical implications
8. **Future Research**: Suggest areas for further investigation

Use academic writing style with proper citations and logical structure.
""",
        
        "technical_documentation": """
Transform this content into comprehensive technical documentation:

1. **Overview**: Clear explanation of purpose and scope
2. **Architecture/Structure**: Detailed breakdown of components and relationships
3. **Implementation Details**: Step-by-step procedures and technical specifications
4. **Configuration**: Setup and configuration requirements
5. **Usage Examples**: Practical examples with code snippets where applicable
6. **Troubleshooting**: Common issues and solutions
7. **Best Practices**: Recommended approaches and patterns
8. **References**: Additional resources and documentation

Format as professional technical documentation with clear sections, code blocks, and diagrams where helpful.
""",
        
        "content_enhancement": """
Enhance and expand this content while maintaining its core message:

1. **Improved Structure**: Reorganize content with clear hierarchy and flow
2. **Enhanced Clarity**: Simplify complex concepts and improve readability
3. **Additional Context**: Add relevant background information and explanations
4. **Examples and Illustrations**: Include practical examples and case studies
5. **Updated References**: Add current statistics, studies, or developments
6. **Actionable Insights**: Provide concrete takeaways and applications
7. **Visual Elements**: Suggest charts, diagrams, or other visual aids
8. **Engagement Elements**: Add questions, exercises, or interactive components

Create engaging, comprehensive content that adds significant value to the original.
""",
        
        "research_analysis": """
Conduct thorough research analysis of the provided materials:

1. **Research Questions**: Identify the key research questions being addressed
2. **Literature Review**: Synthesize existing knowledge and identify gaps
3. **Data Analysis**: Examine evidence, statistics, and supporting data
4. **Methodology Critique**: Evaluate research design and data collection methods
5. **Findings Summary**: Clearly present key discoveries and results
6. **Limitations**: Acknowledge constraints and potential weaknesses
7. **Recommendations**: Provide evidence-based recommendations
8. **Impact Assessment**: Evaluate significance and broader implications

Present analysis in academic format with critical thinking and objective evaluation.
""",
        
        "creative_adaptation": """
Creatively adapt and reimagine this content for modern audiences:

1. **Contemporary Relevance**: Connect traditional concepts to current issues
2. **Narrative Enhancement**: Improve storytelling and engagement
3. **Cultural Translation**: Make content accessible across cultural boundaries
4. **Modern Examples**: Use contemporary analogies and references
5. **Interactive Elements**: Suggest ways to engage readers actively
6. **Multi-Media Integration**: Recommend complementary media (videos, podcasts, etc.)
7. **Practical Applications**: Show how concepts apply to daily life
8. **Discussion Prompts**: Create questions for further exploration

Balance creativity with accuracy, making content both engaging and educational.
"""
    }


def print_example_prompts():
    """Print all available example prompts with descriptions."""
    prompts = get_example_prompts()
    
    print("📋 Available Example Prompts:")
    print("=" * 50)
    
    for name, prompt in prompts.items():
        # Create a readable name
        display_name = name.replace('_', ' ').title()
        
        # Get first line as description
        first_line = prompt.split('\n')[0]
        
        print(f"\n🔸 {display_name}")
        print(f"   {first_line}")
        print(f"   Usage: get_example_prompts()['{name}']")
    
    print(f"\n💡 Total prompts available: {len(prompts)}")
    print("\nTo use a prompt:")
    print("from custom_books.utils.examples import get_example_prompts")
    print("prompts = get_example_prompts()")
    print("my_prompt = prompts['chinese_text_processing']")


def get_prompt_categories() -> Dict[str, List[str]]:
    """
    Get prompts organized by category.
    
    Returns:
        Dictionary mapping categories to lists of prompt names
    """
    return {
        "Language & Translation": [
            "chinese_text_processing"
        ],
        "Academic & Research": [
            "academic_synthesis",
            "research_analysis"
        ],
        "Technical & Documentation": [
            "technical_documentation"
        ],
        "Content Creation": [
            "content_enhancement",
            "creative_adaptation"
        ]
    }


def get_prompts_by_category(category: str) -> Dict[str, str]:
    """
    Get all prompts in a specific category.
    
    Args:
        category: Category name (see get_prompt_categories() for available categories)
        
    Returns:
        Dictionary of prompt names to prompt text for the specified category
    """
    categories = get_prompt_categories()
    all_prompts = get_example_prompts()
    
    if category not in categories:
        available = ", ".join(categories.keys())
        raise ValueError(f"Category '{category}' not found. Available: {available}")
    
    prompt_names = categories[category]
    return {name: all_prompts[name] for name in prompt_names if name in all_prompts}