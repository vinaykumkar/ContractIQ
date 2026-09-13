/** Fixed aurora-mesh background + film grain. Purely decorative. */
export function AuroraBackground() {
  return (
    <>
      <div className="ci-aurora" aria-hidden="true">
        <div className="ci-aurora-blob" />
      </div>
      <div className="ci-grain" aria-hidden="true" />
    </>
  )
}
