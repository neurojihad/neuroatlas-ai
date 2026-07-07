import { BackgroundLayer } from "../../layout/BackgroundLayer";

function AuthLayout({ children }) {
  return (
    <>
      <BackgroundLayer />
      <div className="auth-page">{children}</div>
    </>
  );
}

export default AuthLayout;
