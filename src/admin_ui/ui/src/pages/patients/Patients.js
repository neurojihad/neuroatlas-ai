import { Route, Routes } from "react-router-dom";

import PatientProfile from "./ui/PatientProfile";
import PatientsList from "./ui/PatientsList";

function Patients() {
  return (
    <Routes>
      <Route index element={<PatientsList />} />
      <Route path=":patientId" element={<PatientProfile />} />
    </Routes>
  );
}

export default Patients;
