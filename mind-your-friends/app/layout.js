import './globals.css';

export const metadata = {
  title: 'Mind Your Friends',
  description: 'A real-time multiplayer social trivia game.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
