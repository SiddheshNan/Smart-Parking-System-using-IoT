import React, { useState, useEffect, useRef } from "react";
import { createLocalTimeFromEpoch, WS_URL } from "./helpers";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import {
  faCar,
  faClockRotateLeft,
  faTrash,
  faBan,
} from "@fortawesome/free-solid-svg-icons";
import { faCircleCheck } from "@fortawesome/free-regular-svg-icons";

function RelatimeBox({ slot, isVaccent, at }) {
  return (
    <div
      className={`rounded-lg shadow-md text-center font-bold text-lg p-5 border border ${
        isVaccent ? "bg-green-500" : "bg-red-500"
      } text-white`}
    >
      <h2>Parking Slot : {slot}</h2>
      <h1 className="text-3xl">
        {isVaccent ? (
          <>
            <FontAwesomeIcon className="inline-block" icon={faCircleCheck} />{" "}
            Available
          </>
        ) : (
          <>
            <FontAwesomeIcon className="inline-block" icon={faBan} /> Occupied
          </>
        )}
      </h1>
      <h3 className="text-md mt-1">{at !== "N/A" && createLocalTimeFromEpoch(at)}</h3>
    </div>
  );
}

function HistoryComponent({ inTime, outTime, charge, slot }) {
  return (
    <tr className="border-b">
      <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">
        {slot}
      </td>
      <td className="text-sm text-gray-900 font-normal px-6 py-4 whitespace-nowrap">
        {createLocalTimeFromEpoch(inTime)}
      </td>
      <td className="text-sm text-gray-900 font-normal px-6 py-4 whitespace-nowrap">
        {createLocalTimeFromEpoch(outTime)}
      </td>

      <td className="font-normal px-6 py-4 whitespace-nowrap">₹ {charge}</td>

      <td className="whitespace-nowrap  px-6 py-4 flex justify-center">
        <button
          onClick={() => {
            toast.error("🦄 Wow so easy!", {
              position: "top-right",
              autoClose: 5000,
              hideProgressBar: false,
              closeOnClick: true,
              pauseOnHover: true,
              draggable: true,
              progress: undefined,
            });
          }}
          style={{ outline: "none !important" }}
          className="focus:outline-none  bg-red-500 hover:bg-red-700 text-white text-sm font-bold py-2 px-5 rounded-full shadow-md"
        >
          <FontAwesomeIcon className="inline-block" icon={faTrash} />
        </button>
      </td>
    </tr>
  );
}

function App() {
  const ws = useRef(null);

  const [state, setState] = useState({
    slot_1: {
      vacant: true,
      time: "N/A",
    },
    slot_2: {
      vacant: true,
      time: "N/A",
    },
    slot_3: {
      vacant: true,
      time: "N/A",
    },
    slot_4: {
      vacant: true,
      time: "N/A",
    },
  });

  useEffect(() => {
    ws.current = new WebSocket(WS_URL);
    ws.current.onopen = () => {
      console.log("ws opened");
    };
    ws.current.onclose = () => {
      console.log("ws closed");
    };

    ws.current.onmessage = (e) => {
      const message = JSON.parse(e.data);
      console.log("e", message);
    };

    return () => ws.current.close();
  }, []);

  return (
    <>
      <div>
        <nav className="flex items-center justify-center flex-wrap bg-indigo-500 py-5 shadow-md">
          <div className="flex items-center flex-shrink-0 text-white mr-6">
            <span className="font-semibold text-3xl tracking-tight">
              ⚡ Smart Parking System using IoT
            </span>
          </div>
        </nav>
      </div>

      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="colored"
      />

      <div className="flex justify-between mt-6">
        <div className="w-1/2 border items-center rounded-lg bg-white border-gray-700 h-full mx-4 pb-10 shadow-lg">
          <h1 className="text-center text-3xl font-bold mt-8 text-gray-800">
            <FontAwesomeIcon className="mr-3" icon={faCar} />
            Realtime Status
          </h1>
          <div className="grid grid-cols-2 gap-4 mx-auto justify-center flex px-8 mt-6">
            <RelatimeBox
              slot="1"
              isVaccent={state.slot_1.vacant}
              at={state.slot_1.time}
            />
            <RelatimeBox
              slot="2"
              isVaccent={state.slot_2.vacant}
              at={state.slot_2.time}
            />
            <RelatimeBox
              slot="3"
              isVaccent={state.slot_3.vacant}
              at={state.slot_3.time}
            />
            <RelatimeBox
              slot="4"
              isVaccent={state.slot_4.vacant}
              at={state.slot_4.time}
            />
          </div>
        </div>

        <div className="w-1/2 border items-center rounded-lg bg-white border-gray-700 h-full mx-4 pb-8 mb-8 shadow-lg">
          <h1 className="text-center text-3xl font-bold mt-8  text-gray-800">
            <FontAwesomeIcon className="mr-3" icon={faClockRotateLeft} />
            Parking History
          </h1>

          <div className="flex flex-col px-12 mt-4 overflow-x-auto">
            <table>
              <thead className="bg-white border-b text-sm text-gray-800">
                <tr>
                  <th scope="col" className="px-6 py-4 text-left">
                    Slot
                  </th>
                  <th scope="col" className="px-6 py-4 text-left">
                    In-Time
                  </th>
                  <th scope="col" className="px-6 py-4 text-left">
                    Out-Time
                  </th>
                  <th scope="col" className="px-6 py-4 text-left">
                    Charge
                  </th>
                  <th scope="col" className="px-6 py-4 text-left">
                    Delete
                  </th>
                </tr>
              </thead>
              <tbody className="text-gray-900">
                <HistoryComponent
                  slot={1}
                  inTime={Date.now()}
                  outTime={Date.now()}
                  charge={500}
                />
                <HistoryComponent
                  slot={1}
                  inTime={Date.now()}
                  outTime={Date.now()}
                  charge={500}
                />

                <HistoryComponent
                  slot={1}
                  inTime={Date.now()}
                  outTime={Date.now()}
                  charge={500}
                />
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
