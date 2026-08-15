import { InterviewSession } from '@/types';

const MOCK_QUESTION_BANK = [
  (job: string) =>
    `Thank you for introducing yourself. Looking at the requirements for the **${job}** position, could you walk me through a complex architectural or technical problem you solved recently, and what tradeoffs you evaluated?`,
  () =>
    `That gives great context. How do you approach testing, code quality, and performance monitoring when shipping code under tight deadlines?`,
  (job: string) =>
    `In a high-impact **${job}** role, collaboration with product and design is critical. Can you describe a scenario where you disagreed with a technical or product requirement and how you reached alignment?`,
  () =>
    `Let's discuss failure modes. Tell me about a critical bug or production incident you investigated. What was your root cause analysis approach and what safeguards did you put in place?`,
  () =>
    `Excellent. To wrap up our questions: What are you looking for most in your next team and technical culture, and what questions do you have about the role?`,
];

export async function generateMockAiResponse(
  session: InterviewSession,
  _userResponse: string
): Promise<{ reply: string; isComplete: boolean }> {
  // Simulate AI thinking time
  await new Promise((resolve) => setTimeout(resolve, 1100));

  const assistantMsgCount = session.messages.filter((m) => m.role === 'assistant').length;

  if (assistantMsgCount >= 5) {
    return {
      reply: `Thank you for completing this technical interview! You demonstrated strong communication, thoughtful problem-solving, and practical technical depth suited for the **${session.jobTitle}** role.\n\n### 🎯 Interview Assessment Summary:\n- **Technical Communication:** Excellent clarity and structured answers.\n- **Problem Solving:** Good attention to tradeoffs and edge cases.\n- **Role Fit:** High alignment with job competencies.\n\nOur hiring team will review your complete transcript and follow up with next steps!`,
      isComplete: true,
    };
  }

  const questionGenerator = MOCK_QUESTION_BANK[assistantMsgCount - 1] || MOCK_QUESTION_BANK[0];
  const nextQuestion = questionGenerator(session.jobTitle);

  return {
    reply: nextQuestion,
    isComplete: false,
  };
}
