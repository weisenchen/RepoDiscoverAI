"""
Project Similarity Calculation for RepoDiscoverAI

Finds and recommends similar repositories based on various factors.

Usage:
    python -m app.core.similarity
"""

import json
import math
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path


class ProjectSimilarity:
    """Calculates similarity between repositories."""
    
    def __init__(self):
        # Weights for different similarity factors
        self.weights = {
            "topics": 0.35,        # Shared topics/tags
            "language": 0.20,      # Same programming language
            "description": 0.20,   # Textual similarity
            "stars": 0.15,         # Similar popularity
            "category": 0.10       # Same category/domain
        }
    
    def jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def topics_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity based on topics/tags."""
        topics1 = repo1.get("topics", [])
        topics2 = repo2.get("topics", [])
        
        if isinstance(topics1, str):
            try:
                topics1 = json.loads(topics1)
            except:
                topics1 = []
        if isinstance(topics2, str):
            try:
                topics2 = json.loads(topics2)
            except:
                topics2 = []
        
        set1 = set(t.lower() for t in topics1)
        set2 = set(t.lower() for t in topics2)
        
        return self.jaccard_similarity(set1, set2)
    
    def language_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity based on programming language."""
        lang1 = repo1.get("language", "")
        lang2 = repo2.get("language", "")
        
        if not lang1 or not lang2:
            return 0.5  # Neutral if unknown
        
        return 1.0 if lang1.lower() == lang2.lower() else 0.0
    
    def description_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity based on description text."""
        desc1 = repo1.get("description", "").lower()
        desc2 = repo2.get("description", "").lower()
        
        if not desc1 or not desc2:
            return 0.5  # Neutral if no description
        
        # Simple word overlap
        words1 = set(desc1.split())
        words2 = set(desc2.split())
        
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "for", "with", "and", "or", "in", "on", "to", "of"}
        words1 -= stop_words
        words2 -= stop_words
        
        if not words1 or not words2:
            return 0.5
        
        return self.jaccard_similarity(words1, words2)
    
    def popularity_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity based on star count (similar popularity)."""
        stars1 = repo1.get("stargazers_count", 0)
        stars2 = repo2.get("stargazers_count", 0)
        
        if stars1 == 0 and stars2 == 0:
            return 1.0
        
        # Use log scale to compare
        log_stars1 = math.log10(stars1 + 1)
        log_stars2 = math.log10(stars2 + 1)
        
        # Calculate difference ratio
        max_stars = max(log_stars1, log_stars2)
        min_stars = min(log_stars1, log_stars2)
        
        if max_stars == 0:
            return 1.0
        
        ratio = min_stars / max_stars
        return ratio
    
    def category_similarity(self, repo1: Dict, repo2: Dict) -> float:
        """Calculate similarity based on category."""
        # Infer category from topics
        topics1 = repo1.get("topics", [])
        topics2 = repo2.get("topics", [])
        
        if isinstance(topics1, str):
            try:
                topics1 = json.loads(topics1)
            except:
                topics1 = []
        if isinstance(topics2, str):
            try:
                topics2 = json.loads(topics2)
            except:
                topics2 = []
        
        # Define category keywords
        categories = {
            "ml": ["machine-learning", "deep-learning", "ai", "neural-network", "tensorflow", "pytorch"],
            "web": ["web", "frontend", "backend", "react", "vue", "angular", "django", "flask"],
            "data": ["data-science", "data-analysis", "visualization", "pandas", "numpy"],
            "devops": ["devops", "docker", "kubernetes", "ci-cd", "deployment"],
            "mobile": ["mobile", "ios", "android", "react-native", "flutter"],
            "tools": ["cli", "tool", "utility", "library", "framework"]
        }
        
        def get_category(topics):
            topics_lower = [t.lower() for t in topics]
            for cat, keywords in categories.items():
                if any(kw in topics_lower for kw in keywords):
                    return cat
            return "other"
        
        cat1 = get_category(topics1)
        cat2 = get_category(topics2)
        
        return 1.0 if cat1 == cat2 else 0.0
    
    def calculate_similarity(self, repo1: Dict, repo2: Dict) -> Dict:
        """Calculate comprehensive similarity between two repos."""
        scores = {
            "topics": self.topics_similarity(repo1, repo2),
            "language": self.language_similarity(repo1, repo2),
            "description": self.description_similarity(repo1, repo2),
            "popularity": self.popularity_similarity(repo1, repo2),
            "category": self.category_similarity(repo1, repo2)
        }
        
        # Weighted overall similarity
        overall = sum(
            scores[key] * self.weights[key]
            for key in self.weights
        )
        
        return {
            "overall": round(overall, 4),
            "breakdown": {k: round(v, 4) for k, v in scores.items()},
            "repo1": repo1.get("full_name", ""),
            "repo2": repo2.get("full_name", "")
        }
    
    def find_similar_repos(self, target_repo: Dict, all_repos: List[Dict], 
                          limit: int = 10, min_similarity: float = 0.3) -> List[Dict]:
        """Find repositories similar to the target."""
        similarities = []
        
        for repo in all_repos:
            if repo.get("full_name") == target_repo.get("full_name"):
                continue  # Skip self
            
            sim = self.calculate_similarity(target_repo, repo)
            
            if sim["overall"] >= min_similarity:
                sim["repo"] = repo
                similarities.append(sim)
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["overall"], reverse=True)
        
        # Return top N
        return similarities[:limit]
    
    def batch_similarity(self, repos: List[Dict]) -> Dict[str, List[Dict]]:
        """Calculate similar repos for all repositories."""
        results = {}
        
        for repo in repos:
            similar = self.find_similar_repos(repo, repos, limit=5)
            results[repo.get("full_name", "")] = similar
        
        return results


def main():
    """Test the similarity system."""
    # Test repos
    repo1 = {
        "full_name": "tensorflow/tensorflow",
        "stargazers_count": 170000,
        "language": "Python",
        "description": "An Open Source Machine Learning Framework for Everyone",
        "topics": ["machine-learning", "deep-learning", "ai", "python", "tensorflow"]
    }
    
    repo2 = {
        "full_name": "pytorch/pytorch",
        "stargazers_count": 70000,
        "language": "Python",
        "description": "Tensors and Dynamic neural networks in Python",
        "topics": ["machine-learning", "deep-learning", "ai", "python", "pytorch"]
    }
    
    repo3 = {
        "full_name": "facebook/react",
        "stargazers_count": 200000,
        "language": "JavaScript",
        "description": "A declarative, efficient, and flexible JavaScript library",
        "topics": ["javascript", "react", "frontend", "web", "ui"]
    }
    
    similarity = ProjectSimilarity()
    
    print("=" * 60)
    print("Repository Similarity Test")
    print("=" * 60)
    
    sim_1_2 = similarity.calculate_similarity(repo1, repo2)
    print(f"\n{repo1['full_name']} vs {repo2['full_name']}:")
    print(f"  Overall: {sim_1_2['overall']}")
    print(f"  Topics:  {sim_1_2['breakdown']['topics']}")
    print(f"  Language: {sim_1_2['breakdown']['language']}")
    
    sim_1_3 = similarity.calculate_similarity(repo1, repo3)
    print(f"\n{repo1['full_name']} vs {repo3['full_name']}:")
    print(f"  Overall: {sim_1_3['overall']}")
    print(f"  Topics:  {sim_1_3['breakdown']['topics']}")
    print(f"  Language: {sim_1_3['breakdown']['language']}")
    
    print("\n" + "=" * 60)
    print("Expected: TensorFlow & PyTorch should be more similar than TensorFlow & React")
    print("=" * 60)


if __name__ == "__main__":
    main()
