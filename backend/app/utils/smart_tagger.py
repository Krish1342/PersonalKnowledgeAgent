"""
Smart tagging system using AI to auto-categorize content.
"""

from typing import List, Optional, Tuple
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings


# Predefined tag categories for consistency
PREDEFINED_TAGS = {
    "type": ["article", "note", "code", "documentation", "tutorial", "research", "idea", "todo", "reference"],
    "topic": ["technology", "science", "business", "health", "education", "finance", "programming", "design", "personal"],
    "language": ["python", "javascript", "typescript", "rust", "go", "java", "sql", "markdown", "html", "css"],
    "priority": ["high-priority", "medium-priority", "low-priority"],
}


class SmartTagger:
    """AI-powered automatic content tagging."""
    
    def __init__(self):
        self._llm: Optional[ChatGroq] = None
    
    def _get_llm(self) -> ChatGroq:
        """Lazy initialize LLM."""
        if self._llm is None:
            self._llm = ChatGroq(
                model=settings.GROQ_MODEL_NAME,
                api_key=settings.GROQ_API_KEY,
                temperature=0.3,  # Low temperature for consistent tagging
                max_tokens=200,
            )
        return self._llm
    
    def extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using regex patterns."""
        keywords = []
        
        # Programming languages
        lang_patterns = {
            "python": r'\b(python|\.py|import\s+\w+|def\s+\w+|class\s+\w+)\b',
            "javascript": r'\b(javascript|\.js|const\s+\w+|function\s+\w+|=>)\b',
            "typescript": r'\b(typescript|\.ts|interface\s+\w+|type\s+\w+)\b',
            "rust": r'\b(rust|\.rs|fn\s+\w+|impl\s+\w+|pub\s+fn)\b',
            "sql": r'\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE TABLE)\b',
        }
        
        for lang, pattern in lang_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                keywords.append(lang)
        
        # Content type detection
        if re.search(r'```[\w]*\n', content):
            keywords.append("code")
        if re.search(r'^#+\s+', content, re.MULTILINE):
            keywords.append("documentation")
        if re.search(r'\b(TODO|FIXME|NOTE)\b:', content):
            keywords.append("todo")
        if re.search(r'https?://\S+', content):
            keywords.append("reference")
        
        return list(set(keywords))
    
    def generate_title(self, content: str) -> str:
        """Generate a concise title for content."""
        # First, try to extract existing title
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()[:100]
        
        # Try to get first meaningful line
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                return line[:100] + ("..." if len(line) > 100 else "")
        
        return content[:100].strip() + "..."
    
    def generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a brief summary of content."""
        # For short content, return as is
        if len(content) <= max_length:
            return content
        
        # Try to get first paragraph
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('#') and len(para) > 50:
                return para[:max_length] + ("..." if len(para) > max_length else "")
        
        return content[:max_length].strip() + "..."
    
    async def auto_tag_with_ai(self, content: str) -> List[str]:
        """Use AI to generate relevant tags."""
        try:
            llm = self._get_llm()
            
            system_prompt = """You are a content categorization assistant. 
Analyze the given content and return ONLY a comma-separated list of relevant tags.
Use lowercase tags with hyphens for multi-word tags.
Return 3-7 tags maximum.
Focus on: content type, topic, technology, and importance.
Example output: python, tutorial, api-design, intermediate"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Content to tag:\n\n{content[:2000]}")  # Limit content length
            ]
            
            response = await llm.ainvoke(messages)
            
            # Parse tags from response
            tags_text = response.content.strip()
            tags = [tag.strip().lower().replace(' ', '-') for tag in tags_text.split(',')]
            
            # Filter valid tags
            tags = [t for t in tags if t and len(t) > 1 and len(t) < 50]
            
            return tags[:7]  # Max 7 tags
            
        except Exception as e:
            # Fallback to keyword extraction
            return self.extract_keywords(content)
    
    def suggest_tags(self, content: str) -> List[str]:
        """Synchronously suggest tags based on content analysis."""
        suggested = self.extract_keywords(content)
        
        # Add content-based suggestions
        content_lower = content.lower()
        
        # Topic detection
        topic_keywords = {
            "technology": ["software", "hardware", "tech", "computer", "digital"],
            "science": ["research", "study", "experiment", "hypothesis", "data"],
            "programming": ["code", "function", "variable", "algorithm", "debug"],
            "business": ["company", "startup", "revenue", "market", "strategy"],
            "personal": ["journal", "thought", "reflection", "diary", "feeling"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                suggested.append(topic)
        
        return list(set(suggested))[:7]
    
    def categorize_content(self, content: str) -> dict:
        """Full content analysis returning title, summary, and tags."""
        return {
            "title": self.generate_title(content),
            "summary": self.generate_summary(content),
            "tags": self.suggest_tags(content),
            "keywords": self.extract_keywords(content),
        }


# Singleton
_smart_tagger: Optional[SmartTagger] = None


def get_smart_tagger() -> SmartTagger:
    """Get singleton SmartTagger instance."""
    global _smart_tagger
    if _smart_tagger is None:
        _smart_tagger = SmartTagger()
    return _smart_tagger
