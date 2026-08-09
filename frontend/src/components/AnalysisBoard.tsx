import { useState } from "react";
import { Chessboard } from "react-chessboard";

interface Props {
    chessPosition: string;
    editable: boolean;
    onMove: (
        from: string,
        to: string,
        promotion?: string
    ) => boolean;
}

export default function AnalysisBoard({
    chessPosition,
    editable,
    onMove,
}: Props) {
    const [selectedSquare, setSelectedSquare] = useState<string | null>(
        null
    );

    function onSquareClick({ square }: { square: string }) {
        if (!editable) {
            setSelectedSquare(null);
            return;
        }

        if (selectedSquare === null) {
            setSelectedSquare(square);
            return;
        }

        if (selectedSquare === square) {
            setSelectedSquare(null);
            return;
        }

        onMove(selectedSquare, square, "q");
        setSelectedSquare(null);
    }


    const optionSquares = selectedSquare
        ? {
            [selectedSquare]: {
                backgroundColor: "rgba(250, 204, 21, 0.55)",
            },
        } : {};


    const chessboardOptions = {
        id: "click-to-move",
        allowDragging: false,
        onSquareClick,
        position: chessPosition,
        squareStyles: optionSquares,

        animationDuration: 300,

    };

    return <Chessboard options={chessboardOptions} />;
}