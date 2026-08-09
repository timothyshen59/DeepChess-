import { useEffect } from "react";

type ArrowNavigationOptions = {
    onPrevious: () => void;
    onNext: () => void;
};

export function useArrowNavigation({
    onPrevious,
    onNext,
}: ArrowNavigationOptions) {
    useEffect(() => {
        function handleKeyDown(event: KeyboardEvent) {
            const target = event.target as HTMLElement;

            const isTyping =
                target.tagName === "INPUT" ||
                target.tagName === "TEXTAREA" ||
                target.tagName === "SELECT" ||
                target.isContentEditable;

            if (isTyping) {
                return;
            }

            if (event.key === "ArrowLeft") {
                event.preventDefault();
                onPrevious();
            }

            if (event.key === "ArrowRight") {
                event.preventDefault();
                onNext();
            }
        }

        window.addEventListener("keydown", handleKeyDown);

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [onPrevious, onNext]);
}