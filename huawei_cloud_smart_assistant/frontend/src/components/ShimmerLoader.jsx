export function ShimmerLoader({ lines = 4 }) {
  return (
    <div className="shimmer-container">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="shimmer-line" />
      ))}
    </div>
  );
}
