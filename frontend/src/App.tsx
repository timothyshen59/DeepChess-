import ChessWorkspace from "./components/ChessWorkspace";

export default function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <div className="w-full max-w-5xl">
        <h1 className="mb-6 text-center text-3xl font-bold">
          DeepChess Explore Mode
        </h1>

        <ChessWorkspace />
      </div>
    </main>
  );
}