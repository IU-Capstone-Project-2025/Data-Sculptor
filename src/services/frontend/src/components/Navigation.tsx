import logo from "../assets/icons/logo.svg";
import home from "../assets/icons/home.svg";
import profile from "../assets/icons/profile.svg";
import settings from "../assets/icons/settings.svg";
import "./Navigation.css";

function Navigation() {
  return (
    <nav>
      <img className="nav-item" src={logo} />
      <div className="nav-item" />
      <img className="nav-item" src={home} />
      <img className="nav-item" src={profile} />
      <img className="nav-item" src={settings} />
      <div className="nav-item" id="filler" />
    </nav>
  );
}

export default Navigation;
