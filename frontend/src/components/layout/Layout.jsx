import { Outlet } from 'react-router-dom';
import Nav from './Nav.jsx';
import styles from './Layout.module.css';

export default function Layout() {
  return (
    <div className={styles.root}>
      <Nav />
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span>CourtVision</span>
          <span>Data via nba_api. Team stats only.</span>
        </div>
      </footer>
    </div>
  );
}
