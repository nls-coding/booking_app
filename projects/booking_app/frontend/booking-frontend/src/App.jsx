import React, { useEffect, useState } from "react";
import { listSpots, getPlansBySpot, listUsers, listReservationsByDate, createReservation } from "./api";

export default function App() {
  const [spots, setSpots] = useState([]);
  const [spotId, setSpotId] = useState(null);
  const [plans, setPlans] = useState([]);
  const [users, setUsers] = useState([]);
  const [date, setDate] = useState(new Date().toISOString().slice(0,10)); // YYYY-MM-DD
  const [resv, setResv] = useState([]);
  const [form, setForm] = useState({ user_id:"", plan_id:"", start:"", end:"", note:"" });

  useEffect(() => {
    (async () => {
      const s = await listSpots();
      setSpots(s.data || []);
      if (s.data?.[0]) setSpotId(s.data[0].booking_spot_id);
      const u = await listUsers();
      setUsers(u.data || []);
    })();
  }, []);

  useEffect(() => {
    if (!spotId) return;
    (async () => {
      const p = await getPlansBySpot(spotId);
      setPlans(p.data || []);
    })();
  }, [spotId]);

  useEffect(() => {
    (async () => {
      const r = await listReservationsByDate(date);
      setResv(r.data || []);
    })();
  }, [date]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.user_id || !form.plan_id || !form.start || !form.end) return alert("必須項目を入力してください");
    const payload = {
      user_id: Number(form.user_id),
      plan_id: Number(form.plan_id),
      start_datetime: new Date(`${date}T${form.start}:00Z`).toISOString(),
      end_datetime:   new Date(`${date}T${form.end}:00Z`).toISOString(),
      note: form.note || ""
    };
    const res = await createReservation(payload);
    if (res.error) {
      alert(`${res.error.code}: ${res.error.message}`);
    } else {
      setForm({ user_id:"", plan_id:"", start:"", end:"", note:"" });
      const r = await listReservationsByDate(date);
      setResv(r.data || []);
    }
  };

  return (
    <div className="container">
      <h1>予約サイト（MVP）</h1>

      <div className="card">
        <h3>1) スポット / プラン / 日付選択</h3>
        <div className="row">
          <label>
            スポット：
            <select value={spotId || ""} onChange={e=>setSpotId(Number(e.target.value))}>
              {spots.map(s => <option key={s.booking_spot_id} value={s.booking_spot_id}>{s.name}</option>)}
            </select>
          </label>
          <label>
            表示日：
            <input type="date" value={date} onChange={e=>setDate(e.target.value)} />
          </label>
        </div>
      </div>

      <div className="card">
        <h3>2) 予約作成</h3>
        <form onSubmit={submit} className="row">
          <label>
            ユーザー：
            <select value={form.user_id} onChange={e=>setForm({...form, user_id:e.target.value})}>
              <option value="">選択</option>
              {users.map(u => <option key={u.user_id} value={u.user_id}>{u.name}</option>)}
            </select>
          </label>
          <label>
            プラン：
            <select value={form.plan_id} onChange={e=>setForm({...form, plan_id:e.target.value})}>
              <option value="">選択</option>
              {plans.map(p => <option key={p.plan_id} value={p.plan_id}>{p.name}</option>)}
            </select>
          </label>
          <label>
            開始(HH:MM)：
            <input type="time" value={form.start} onChange={e=>setForm({...form, start:e.target.value})}/>
          </label>
          <label>
            終了(HH:MM)：
            <input type="time" value={form.end} onChange={e=>setForm({...form, end:e.target.value})}/>
          </label>
          <label style={{flex:"1"}}>
            備考：
            <input value={form.note} onChange={e=>setForm({...form, note:e.target.value})}/>
          </label>
          <button type="submit">予約する</button>
        </form>
      </div>

      <div className="card">
        <h3>3) 当日の予約（カレンダー風・日表示）</h3>
        <table className="table">
          <thead>
            <tr><th>時間</th><th>ユーザー</th><th>プラン</th><th>メモ</th></tr>
          </thead>
        <tbody>
          {resv.map(r => (
            <tr key={r.reservation_id}>
              <td>
                <span className="badge">
                  {new Date(r.start_datetime).toISOString().slice(11,16)} - {new Date(r.end_datetime).toISOString().slice(11,16)}
                </span>
              </td>
              <td>{r.user?.name}</td>
              <td>{r.plan?.name}</td>
              <td>{r.note || "-"}</td>
            </tr>
          ))}
          {resv.length === 0 && (
            <tr><td colSpan="4">予約はありません</td></tr>
          )}
        </tbody>
        </table>
        <p style={{opacity:.7}}>※ まずは日表示の簡易テーブル。必要があれば <code>react-big-calendar</code> などに置き換え可能。</p>
      </div>
    </div>
  );
}
