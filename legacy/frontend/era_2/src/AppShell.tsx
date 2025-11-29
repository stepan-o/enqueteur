import { Link, Outlet, useLocation } from "react-router-dom";
import styles from "./AppShell.module.css";

export default function AppShell() {
  const { pathname } = useLocation();
  // Explicit active-state logic so only one of Stage/Details/Episodes is active at a time
  const isStage = pathname === "/" || /^\/episodes\/[^/]+\/stage$/.test(pathname);
  const isDetails = pathname === "/episodes/latest" || /^\/episodes\/[^/]+$/.test(pathname);
  const isEpisodes = pathname === "/episodes"; // index only
  // If regex overlap ever occurs, enforce single-active preference order: Details > Stage > Episodes
  const active = {
    stage: isStage && !isDetails && !isEpisodes,
    details: isDetails && !isEpisodes,
    episodes: isEpisodes,
  };
  return (
    <div className={styles.shell}>
      <nav
        className={styles.nav}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className={styles.navInner}>
          <Link
            to="/"
            className={active.stage ? `${styles.link} ${styles.active}` : styles.link}
            aria-current={active.stage ? "page" : undefined}
          >
            Stage
          </Link>
          <Link
            to="/episodes/latest"
            className={active.details ? `${styles.link} ${styles.active}` : styles.link}
            aria-current={active.details ? "page" : undefined}
          >
            Details
          </Link>
          <Link
            to="/episodes"
            className={active.episodes ? `${styles.link} ${styles.active}` : styles.link}
            aria-current={active.episodes ? "page" : undefined}
          >
            Episodes
          </Link>
          <Link to="/agents" className={styles.link}>
            Agents
          </Link>
          <Link to="/settings" className={styles.link}>
            Settings
          </Link>
        </div>
      </nav>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
