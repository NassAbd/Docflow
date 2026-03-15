import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './index.css';
import { Navbar } from './components/Navbar';
import { UploadPage } from './pages/Upload';
import { CrmPage } from './pages/CRM';
import { CompliancePage } from './pages/Compliance';

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/crm" element={<CrmPage />} />
            <Route path="/compliance" element={<CompliancePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
