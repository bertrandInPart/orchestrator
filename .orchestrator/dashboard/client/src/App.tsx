import { BrowserRouter, Routes, Route } from "react-router-dom";
import { BoardView } from "./views/BoardView";
import { FeatureDetailView } from "./views/FeatureDetailView";

function App() {
  return (
    <BrowserRouter>
      <main className="app">
        <Routes>
          <Route path="/" element={<BoardView />} />
          <Route path="/features/:slug" element={<FeatureDetailView />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
