import { NavLink } from "react-router-dom";

import { hasAnyRole } from "../../shared/constants/roles";
import { menuItems } from "../../shared/constants/menu";
import { useAuth } from "../../shared/hooks/useAuth";

export const Menu = () => {
  const { user } = useAuth();

  return (
    <nav>
      {menuItems
        .filter((item) => hasAnyRole(user?.roles, item.roles))
        .map((item) => (
          <NavLink
            key={item.name}
            to={`/${item.name}`}
            className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
          >
            <span>{item.label}</span>
          </NavLink>
        ))}
    </nav>
  );
};
