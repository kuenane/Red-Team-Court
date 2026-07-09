import React from "react";
import { HashRouter, Routes, Route } from "react-router-dom";
import Upload from "./pages/Upload";
import Courtroom from "./pages/Courtroom";
import Verdict from "./pages/Verdict";
import "./styles.css";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/courtroom/:runId" element={<Courtroom />} />
        <Route path="/verdict/:runId" element={<Verdict />} />
      </Routes>
    </HashRouter>
  );
}
