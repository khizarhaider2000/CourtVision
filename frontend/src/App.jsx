import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout.jsx';
import Home from './pages/Home.jsx';
import Query from './pages/Query.jsx';
import Analytics from './pages/Analytics.jsx';
import Teams from './pages/Teams.jsx';
import Methodology from './pages/Methodology.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/query" element={<Query />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/methodology" element={<Methodology />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
