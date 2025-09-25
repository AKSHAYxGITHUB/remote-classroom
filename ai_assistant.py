import random

def get_ai_response(question, context=""):
    """
    Simulated AI assistant that provides educational responses.
    In a production environment, this would integrate with a real AI service like OpenAI GPT or Google Gemini.
    """
    
    # Convert question to lowercase for easier matching
    question_lower = question.lower()
    
    # Educational responses based on common question patterns
    responses = {
        'what': [
            f"Based on the course context, {question} is an important topic. Let me explain: This concept involves understanding the fundamental principles and their practical applications.",
            f"Great question! {question} refers to a key concept in this subject. It's essential to understand the underlying mechanisms and how they relate to real-world scenarios.",
        ],
        'how': [
            f"To understand {question}, let's break it down step by step: First, identify the key components. Then, analyze their relationships. Finally, apply the principles systematically.",
            f"Here's how to approach {question}: Start with the basics, build your understanding gradually, and practice with examples from the course materials.",
        ],
        'why': [
            f"The reason behind {question} relates to fundamental principles in this field. Understanding this concept is crucial because it forms the foundation for more advanced topics.",
            f"Good question about why this happens! This occurs due to the interaction of several factors that we've covered in the course materials.",
        ],
        'define': [
            f"The definition of this concept is: A fundamental principle or element that plays a crucial role in understanding the subject matter.",
            f"This term refers to an important concept that you'll encounter frequently in this course.",
        ],
        'explain': [
            f"Let me explain this concept: It involves understanding the core principles and how they apply to practical situations. The key is to see the connections between different elements.",
            f"This is an excellent topic to explore! The explanation involves breaking down complex ideas into manageable parts and showing how they work together.",
        ]
    }
    
    # Find appropriate response based on question type
    for keyword in responses:
        if keyword in question_lower:
            response = random.choice(responses[keyword])
            if context:
                response += f"\n\nBased on your course materials: {context[:200]}..."
            return response
    
    # Default educational responses
    default_responses = [
        f"That's an insightful question about '{question}'. This topic is fundamental to understanding the broader concepts we're studying. I'd recommend reviewing the course materials for detailed explanations and examples.",
        f"Excellent question! '{question}' is an important concept. To fully grasp this, consider how it relates to other topics we've covered and look for practical examples in your course materials.",
        f"Great thinking! Your question about '{question}' shows you're engaging deeply with the material. This concept connects to several key principles we've discussed in class.",
        f"I appreciate your curiosity about '{question}'. This is a complex topic that benefits from multiple perspectives. Have you reviewed the related materials in this course?",
        f"Your question about '{question}' touches on some important fundamentals. I'd suggest exploring the course materials and practicing with examples to deepen your understanding.",
    ]
    
    response = random.choice(default_responses)
    
    if context and len(context) > 50:
        response += f"\n\nReference from course materials: {context[:200]}..."
    
    return response

# Test the AI assistant
if __name__ == '__main__':
    test_questions = [
        "What is photosynthesis?",
        "How do I solve quadratic equations?",
        "Why is Hindi literature important?",
        "Explain the water cycle",
        "Define democracy",
    ]
    
    for question in test_questions:
        print(f"Q: {question}")
        print(f"A: {get_ai_response(question)}")
        print("-" * 50)