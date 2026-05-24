import { useState } from "react"
const BACKEND = "https://8000-cs-efc09588-b0d2-4105-8e46-481a05e7191c.cs-asia-southeast1-seal.cloudshell.dev"
export default function App() {
  const [idea, setIdea] = useState("")
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  async function launch() {
    setLoading(true)
    try {
      const res = await fetch(BACKEND + "/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea })
      })
      const data = await res.json()
      setResult(data)
    } catch(e) {
      alert("Backend not reachable: " + e.message)
    }
    setLoading(false)
  }
  return (
    <div style={{padding:"2rem",fontFamily:"sans-serif",maxWidth:"800px",margin:"0 auto"}}>
      <h1 style={{color:"#534AB7"}}>AI Company</h1>
      <div style={{display:"flex",gap:"8px",marginBottom:"2rem"}}>
        <input value={idea} onChange={e=>setIdea(e.target.value)}
          onKeyDown={e=>e.key==="Enter"&&launch()}
          placeholder="Enter project idea..."
          style={{flex:1,padding:"10px",fontSize:"15px",borderRadius:"8px",border:"1px solid #ddd"}}/>
        <button onClick={launch} disabled={loading}
          style={{padding:"10px 20px",background:"#534AB7",color:"#fff",border:"none",borderRadius:"8px",cursor:"pointer",fontSize:"15px"}}>
          {loading?"Running...":"Launch"}
        </button>
      </div>
      {result && (
        <div>
          <h2>{result.project_name}</h2>
          <p>{result.description}</p>
          <pre style={{background:"#f5f5f5",padding:"1rem",borderRadius:"8px",overflow:"auto",fontSize:"12px"}}>
            {JSON.stringify(result,null,2)}
          </pre>
        </div>
      )}
    </div>
  )
}

