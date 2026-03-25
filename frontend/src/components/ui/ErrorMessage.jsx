import styles from './ErrorMessage.module.css';

export default function ErrorMessage({ message, onDismiss }) {
  return (
    <div className={styles.error} role="alert">
      <span className={styles.message}>{message}</span>
      {onDismiss && (
        <button className={styles.dismiss} onClick={onDismiss} aria-label="Dismiss error">
          &times;
        </button>
      )}
    </div>
  );
}
