import { Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { HomePage } from '@/pages/HomePage';
import { InterviewRoomPage } from '@/pages/InterviewRoomPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { InterviewProvider } from '@/components/interview-provider';

export function App() {
  return (
    <InterviewProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/interview/:id" element={<InterviewRoomPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </InterviewProvider>
  );
}

export default App;
