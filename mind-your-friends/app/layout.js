import './globals.css';

export const metadata = {
  title: 'Mind Your Friends',
  description: 'AI-powered social trivia party game',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-game-dark text-white min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
