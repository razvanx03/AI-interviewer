import React, { useState, useEffect } from 'react';
import { HomePage } from '@/pages/HomePage';
import { InterviewRoomPage } from '@/pages/InterviewRoomPage';

export function App() {
  const [currentRoute, setCurrentRoute] = useState<{
    page: 'home' | 'interview';
    interviewId?: string;
  }>({ page: 'home' });

  // Parse path and hash on load and on popstate
  useEffect(() => {
    const parseUrl = () => {
      const pathname = window.location.pathname;
      const hash = window.location.hash;

      // Check path /interview/:id
      const pathMatch = pathname.match(/^\/interview\/([a-zA-Z0-9_-]+)/);
      if (pathMatch && pathMatch[1]) {
        setCurrentRoute({ page: 'interview', interviewId: pathMatch[1] });
        return;
      }

      // Check hash #/interview/:id
      const hashMatch = hash.match(/^#\/interview\/([a-zA-Z0-9_-]+)/);
      if (hashMatch && hashMatch[1]) {
        setCurrentRoute({ page: 'interview', interviewId: hashMatch[1] });
        return;
      }

      setCurrentRoute({ page: 'home' });
    };

    parseUrl();
    window.addEventListener('popstate', parseUrl);
    window.addEventListener('hashchange', parseUrl);

    return () => {
      window.removeEventListener('popstate', parseUrl);
      window.removeEventListener('hashchange', parseUrl);
    };
  }, []);

  const navigateToInterview = (id: string) => {
    window.history.pushState(null, '', `/interview/${id}`);
    setCurrentRoute({ page: 'interview', interviewId: id });
  };

  const navigateHome = () => {
    window.history.pushState(null, '', '/');
    setCurrentRoute({ page: 'home' });
  };

  if (currentRoute.page === 'interview' && currentRoute.interviewId) {
    return (
      <InterviewRoomPage interviewId={currentRoute.interviewId} onNavigateHome={navigateHome} />
    );
  }

  return <HomePage onNavigateToInterview={navigateToInterview} />;
}

export default App;
