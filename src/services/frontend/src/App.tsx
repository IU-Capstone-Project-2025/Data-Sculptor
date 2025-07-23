import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import "./App.css";
import vector from "./assets/decorations/vector.svg";
import Navigation from "./components/Navigation";
import NotebookElement from "./components/NotebookElement";

function App() {
  return (
    <>
      <img className="decorations" id="background-decoration-1" src={vector} />
      <img className="decorations" id="background-decoration-2" src={vector} />
      <Navigation />
      <main>
        <Router>
          <Routes>
            <Route
              path="/"
              element={
                <NotebookElement
                  notebookUrl="/profile.ipynb"
                  templateUrl="/template.ipynb"
                />
              }
            />
            <Route path="/notebook/">
              <Route path=":filename" element={<NotebookElement />} />
            </Route>
          </Routes>
        </Router>
      </main>
    </>
  );
}

export default App;
