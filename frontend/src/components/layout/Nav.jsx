import { NavLink } from 'react-router-dom';
import styles from './Nav.module.css';

const NAV_LINKS = [
  { to: '/query', label: 'Query' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/teams', label: 'Teams' },
  { to: '/methodology', label: 'Methodology' },
];

export default function Nav() {
  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.brand}>
          CourtVision
        </NavLink>
        <ul className={styles.links}>
          {NAV_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  isActive ? `${styles.link} ${styles.linkActive}` : styles.link
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
