import React, { useEffect, useRef, useState } from 'react';
import { cn } from '../utils';

// Helper for random colors
const randomColors = (count) => {
    return new Array(count)
        .fill(0)
        .map(() => "#" + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'));
};

export default function TubesBackground({
    children,
    className,
    enableClickInteraction = true
}) {
    const canvasRef = useRef(null);
    const tubesRef = useRef(null);

    useEffect(() => {
        let mounted = true;
        let cleanup;

        const initTubes = async () => {
            if (!canvasRef.current) return;

            try {
                // Load the specialized Tubes library
                const module = await import('https://cdn.jsdelivr.net/npm/threejs-components@0.0.19/build/cursors/tubes1.min.js');
                const TubesCursor = module.default;

                if (!mounted) return;

                const app = TubesCursor(canvasRef.current, {
                    tubes: {
                        colors: ["#f967fb", "#53bc28", "#6958d5"],
                        lights: {
                            intensity: 200,
                            colors: ["#83f36e", "#fe8a2e", "#ff008a", "#60aed5"]
                        }
                    }
                });

                tubesRef.current = app;

                const handleResize = () => {
                    // Additional resize logic if needed
                };

                window.addEventListener('resize', handleResize);

                cleanup = () => {
                    window.removeEventListener('resize', handleResize);
                };

            } catch (error) {
                console.error("Failed to load TubesCursor:", error);
            }
        };

        initTubes();

        return () => {
            mounted = false;
            if (cleanup) cleanup();
        };
    }, []);

    const handleClick = (e) => {
        if (!enableClickInteraction || !tubesRef.current) return;

        // Only randomize colors when clicking empty background space
        // Let buttons/forms have their own pointer-events-auto
        const target = e.target;
        if (target === e.currentTarget || target.tagName === 'CANVAS') {
            const colors = randomColors(3);
            const lightsColors = randomColors(4);

            tubesRef.current.tubes.setColors(colors);
            tubesRef.current.tubes.setLightsColors(lightsColors);
        }
    };

    return (
        <div
            className={cn("fixed inset-0 w-full h-screen overflow-hidden bg-[#050505] -z-10", className)}
            onClick={handleClick}
        >
            <canvas
                ref={canvasRef}
                className="absolute inset-0 w-full h-full block"
                style={{ touchAction: 'none' }}
            />

            {/* Content Overlay wrapped to pass mouse events to canvas appropriately */}
            <div className="relative z-10 w-full h-full pointer-events-none overflow-y-auto">
                {children}
            </div>
        </div>
    );
}
